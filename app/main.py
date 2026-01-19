import asyncio
import logging
import sys
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.agents.voice import VoiceActivityVideoSampler, room_io
from app.llm.gemini import create_llm
from app.avatar.anam_avatar import create_avatar
from app.avatar.persona import SYSTEM_INSTRUCTIONS
from app.utils.safety import keep_alive
from app.core.supabase import supabase

# Configure Advanced Logging for Production Monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dia-presenter-agent")
logger.setLevel(logging.INFO)

async def entrypoint(ctx: JobContext):
    """
    Core entrypoint for the AI Agent worker. 
    Orchestrates slides, Gemini LLM, and Anam Avatar.
    """
    logger.info(f"🚀 Initializing agent for room: {ctx.room.name}")

    # 1. Join Room and Auto-Subscribe to User
    # This ensures the agent can receive audio from the participant for questions.
    try:
        await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
        logger.info("Successfully connected to LiveKit room.")
    except Exception as e:
        logger.error(f"Failed to connect to room: {e}")
        return

    # 2. Extract Session Metadata
    # We wait briefly (2.5s) to ensure the participant's metadata has propagated.
    await asyncio.sleep(2.5) 
    
    presentation_id = None
    # We find the presentation_id passed in the token metadata from routes.py.
    for participant in ctx.room.participants.values():
        if participant.metadata:
            presentation_id = participant.metadata
            logger.info(f"Verified Presentation ID from metadata: {presentation_id}")
            break

    if not presentation_id:
        logger.error("FATAL: No presentation_id found in room metadata. Closing worker.")
        return

    # 3. Fetch Processed Slide Data from Supabase
    # This retrieves the specific slide images and text for the current session.
    logger.info(f"Querying slide manifest for: {presentation_id}")
    try:
        query_result = supabase.table("slides") \
            .select("*") \
            .eq("presentation_id", presentation_id) \
            .order("slide_number", ascending=True) \
            .execute()
        
        slides = query_result.data
        if not slides:
            logger.error(f"Integrity Error: No slides found for ID {presentation_id}")
            return
        logger.info(f"Loaded {len(slides)} slides successfully.")
    except Exception as e:
        logger.error(f"Supabase Query Failed: {e}")
        return

    # 4. Initialize AI Brain (Gemini) and Visuals (Anam)
    llm = create_llm()
    avatar = create_avatar()

    # 5. CRITICAL VISIBILITY CONFIGURATION (Fixes Invisible Avatar)
    # speaking_fps=0 is mandatory to prevent the Agent from publishing its own video.
    # This allows the Anam Avatar plugin to handle the video track exclusively.
    # min_endpointing_delay=2.0 provides the buffer needed for avatar lip-sync.
    session = AgentSession(
        llm=llm,
        video_sampler=VoiceActivityVideoSampler(speaking_fps=0, silent_fps=0),
        preemptive_generation=False,
        min_endpointing_delay=2.0, 
        max_endpointing_delay=5.0,
    )

    # Attach Anam plugin to intercept LLM text and convert it to avatar video.
    await avatar.start(session, room=ctx.room)

    # Define strict presentation persona rules to avoid avatar lag.
    presenter_instructions = (
        f"{SYSTEM_INSTRUCTIONS}\n"
        "GOAL: Present the provided slide deck semantically. "
        "STRICT LIMIT: Maximum 2 sentences per response. Wait for playout."
    )

    # Start the integrated AI service with video enabled.
    await session.start(
        agent=Agent(instructions=presenter_instructions),
        room=ctx.room,
        room_input_options=room_io.RoomInputOptions(video_enabled=True),
    )

    # 6. THE SYNCHRONIZED PRESENTATION LOOP
    logger.info("Starting automated presentation sequence.")
    for slide in slides:
        slide_no = slide["slide_number"]
        image_url = slide["image_url"]
        content_text = slide["extracted_text"]

        # TRIGGER FRONTEND SYNC:
        # Updating local participant attributes triggers a global event in index.html.
        await ctx.room.local_participant.set_attributes({
            "current_slide_url": image_url
        })

        logger.info(f"Displaying Slide {slide_no} to participants.")

        # Command Gemini to synthesize speech for the slide content.
        session.generate_reply(
            instructions=f"Slide {slide_no} Text Content: {content_text}. Present this clearly."
        )

        # WAIT FOR COMPLETION:
        # Ensures audio/video finishes before the agent moves to the next slide.
        await session.wait_for_playout()
        
        # Natural buffer delay between slides.
        await asyncio.sleep(2.0) 

    # 7. Final Handover and Conclusion
    session.generate_reply(instructions="Thank the audience and ask if there are any specific questions.")
    
    logger.info("Sequence Complete. Entering active standby mode.")
    
    # Keep the process alive for user questions/interaction.
    await keep_alive(ctx)

if __name__ == "__main__":
    # Required for the LiveKit CLI to start the worker process.
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
