import os
import uuid
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from livekit import api

# Core logic and config imports
from app.core.supabase import supabase
from app.core.ppt_processor import extract_text_slidewise, convert_ppt_to_images
from app.config import (
    LIVEKIT_API_KEY,
    LIVEKIT_API_SECRET,
    LIVEKIT_URL,
    BUCKET_IMAGES,
    SUPABASE_URL
)

# Standard logging for API tracking
logger = logging.getLogger("api-routes-dia")
router = APIRouter()

@router.post("/upload-ppt")
async def upload_ppt_and_get_token(file: UploadFile = File(...)):
    """
    Unified Endpoint for PPT-to-Avatar workflow.
    1. Validates and processes the .pptx file into assets.
    2. Stores assets in Supabase with foreign key integrity.
    3. Issues a JWT token containing the presentation_id metadata.
    """
    # File Validation: Ensures the backend only attempts to process valid modern PPTX files.
    if not file.filename.endswith(".pptx"):
        logger.error(f"Rejection: Invalid file type uploaded ({file.filename})")
        raise HTTPException(status_code=400, detail="Document must be in .pptx format.")

    # 1. UNIQUE IDENTIFIER GENERATION
    # The presentation_id acts as the 'Primary Key' that connects the Agent to these specific slides.
    presentation_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4()) 
    identity = f"dia_presenter_{uuid.uuid4().hex[:6]}"
    room_name = f"dia_session_{presentation_id[:8]}"
    
    # Create Local Buffer Directory for temporary processing
    work_dir = os.path.join("workdir", presentation_id)
    os.makedirs(work_dir, exist_ok=True)
    ppt_path = os.path.join(work_dir, file.filename)

    try:
        # 2. LOCAL ASSET PROCESSING
        logger.info(f"Buffered PPT upload: {file.filename}")
        with open(ppt_path, "wb") as buffer:
            buffer.write(await file.read())

        # Extract text for Gemini and images for the frontend view.
        image_files = convert_ppt_to_images(ppt_path, work_dir)
        slides_text = extract_text_slidewise(ppt_path)

        # 3. DATABASE PERSISTENCE (PARENTS)
        # Register the session in Supabase before adding individual slides.
        logger.info(f"Registering parent presentation: {presentation_id}")
        supabase.table("presentations").insert({
            "id": presentation_id,
            "user_id": user_id,
            "title": file.filename,
            "total_slides": len(slides_text)
        }).execute()

        # 4. DATABASE PERSISTENCE (CHILDREN / SLIDES)
        # Upload each slide to storage and save metadata for the AI Agent.
        logger.info(f"Uploading {len(slides_text)} slides to storage.")
        for i, slide_data in enumerate(slides_text):
            slide_no = slide_data["slide_number"]
            storage_path = f"{user_id}/{presentation_id}/slide_{slide_no}.jpg"
            
            # Transfer slide image to Supabase Bucket.
            with open(image_files[i], "rb") as image_content:
                supabase.storage.from_(BUCKET_IMAGES).upload(
                    path=storage_path, 
                    file=image_content.read(),
                    file_options={"content-type": "image/jpeg"}
                )
            
            # Public URL for frontend slide display.
            img_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_IMAGES}/{storage_path}"

            # Save metadata for the AI Agent loop.
            supabase.table("slides").insert({
                "presentation_id": presentation_id,
                "user_id": user_id,
                "slide_number": slide_no,
                "image_url": img_url,
                "extracted_text": slide_data["text"]
            }).execute()

        # 5. TOKEN FABRICATION
        # IMPORTANT: The presentation_id is embedded in the token metadata. 
        # The AI Agent reads this to know which slides to explain.
        logger.info(f"Fabricating access token for room: {room_name}")
        token = api.AccessToken(
            LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET
        ).with_identity(identity).with_metadata(presentation_id) 
        
        token.with_grants(api.VideoGrants(room_join=True, room=room_name))
        
        return {
            "status": "success",
            "presentation_id": presentation_id,
            "token": token.to_jwt(),
            "url": LIVEKIT_URL,
            "room": room_name
        }

    except Exception as e:
        logger.error(f"CRITICAL API FAILURE: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Session initialization failed: {str(e)}")
    finally:
        # Cleanup temporary files to prevent disk usage issues on Render.
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)