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

logger = logging.getLogger("api-routes")
router = APIRouter()

@router.post("/upload-ppt")
async def upload_ppt_and_get_token(file: UploadFile = File(...)):
    """
    Unified Route: 
    1. Processes PPT.
    2. Saves data to Supabase.
    3. Returns Token with Presentation ID in Metadata.
    """
    if not file.filename.endswith(".pptx"):
        raise HTTPException(status_code=400, detail="Only .pptx files allowed.")

    # 1. Generate Unique IDs for this session
    presentation_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4()) 
    identity = f"user_{uuid.uuid4().hex[:6]}"
    room_name = f"room_{presentation_id}"
    
    # Create temporary workspace for processing
    work_dir = os.path.join("workdir", presentation_id)
    os.makedirs(work_dir, exist_ok=True)
    ppt_path = os.path.join(work_dir, file.filename)

    try:
        # 2. Save and Process PPT Locally
        with open(ppt_path, "wb") as f:
            f.write(await file.read())

        image_files = convert_ppt_to_images(ppt_path, work_dir)
        slides_text = extract_text_slidewise(ppt_path)

        # 3. Create Parent Presentation Record
        # This prevents Foreign Key errors in Supabase
        supabase.table("presentations").insert({
            "id": presentation_id,
            "user_id": user_id,
            "title": file.filename,
            "total_slides": len(slides_text)
        }).execute()

        # 4. Save Individual Slides (Images & Text)
        for i, slide in enumerate(slides_text):
            slide_no = slide["slide_number"]
            storage_path = f"{user_id}/{presentation_id}/slide_{slide_no}.jpg"
            
            # Upload slide image to Supabase Storage
            supabase.storage.from_(BUCKET_IMAGES).upload(storage_path, image_files[i])
            img_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_IMAGES}/{storage_path}"

            # Save metadata to the slides table
            supabase.table("slides").insert({
                "presentation_id": presentation_id,
                "user_id": user_id,
                "slide_number": slide_no,
                "image_url": img_url,
                "extracted_text": slide["text"]
            }).execute()

        # 5. Generate LiveKit Token
        # Critical: We put presentation_id in metadata so the agent retrieves these specific slides
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
        logger.error(f"❌ Processing Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup temporary files
        shutil.rmtree(work_dir, ignore_errors=True)
