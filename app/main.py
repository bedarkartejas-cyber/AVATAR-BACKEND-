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

# Configure Advanced Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dia-presenter-agent")
logger.setLevel(logging.INFO)

async def entrypoint(ctx: JobContext):
    """
    Core entrypoint for the AI Agent worker. 
    Manages the orchestration between slides, Gemini LLM, and Anam Avatar.
    """
    logger.info(f"🚀 Initializing agent for room: {ctx.room.name}")

    # 1. Join Room and Auto-Subscribe to User (for feedback/questions)
    # This connects the agent to the LiveKit server instance.
    try:
        await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
        logger.info("Successfully connected to LiveKit room.")
    except Exception as e:
        logger.error(f"Failed to connect to room: {e}")
        return

    # 2. Extract Session Metadata
    # We wait briefly to ensure global participant metadata has propagated.
    await asyncio.sleep(2.5) 
    
    presentation_id = None
    for participant in ctx.room.participants.values():
        if participant.metadata:
            presentation_id = participant.metadata
            logger.info(f"Verified Presentation ID from metadata: {presentation_id}")
            break

    if not presentation_id:
        logger.error("FATAL: No presentation_id found in room metadata. Closing worker.")
        return

    # 3. Synchronize Slide Data from Supabase
    # Ensures the Agent only presents content specific to the current user's upload.
    logger.info(f"Querying slide manifest for: {presentation_id}")
    try:
        query_result = supabase.table("slides") \
            .select("*") \
            .eq("presentation_id", presentation_id) \
            .order("slide_number", ascending=True) \
            .execute()
        
        slides = query_result.data
        if not slides:
            logger.error(f"Integrity Error: No slides found for valid presentation ID {presentation_id}")
            return
        logger.info(f"Loaded {len(slides)} slides successfully.")
    except Exception as e:
        logger.error(f"Supabase Query Failed: {e}")
        return

    # 4. Initialize Brain (Gemini) and Visuals (Anam)
    llm = create_llm()
    avatar = create_avatar()

    # 5. CONFIGURE AGENT SESSION (CRITICAL FOR AVATAR STABILITY)
    # speaking_fps=0 is required to prevent the Agent from publishing an empty 
    # video track that would conflict with the Anam plugin's stream.
    # min_endpointing_delay=2.0 provides the buffer needed for video lip-sync.
    session = AgentSession(
        llm=llm,
        video_sampler=VoiceActivityVideoSampler(speaking_fps=0, silent_fps=0),
        preemptive_generation=False,
        min_endpointing_delay=2.0, 
        max_endpointing_delay=5.0,
    )

    # Attach the Anam plugin to the session
    # This allows Anam to intercept text chunks and convert them to video.
    await avatar.start(session, room=ctx.room)

    # Define strict presentation rules for the LLM
    # Prevents 'run-on' speech that can cause the avatar to lag.
    presenter_instructions = (
        f"{SYSTEM_INSTRUCTIONS}\n"
        "GOAL: Present the provided slide deck semantically. "
        "STRICT LIMIT: Maximum 2 sentences per response. Wait for playout."
    )

    # Start the integrated AI service
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
        # Updating local participant attributes triggers a global event 
        # in the index.html via the ParticipantAttributesChanged listener.
        await ctx.room.local_participant.set_attributes({
            "current_slide_url": image_url
        })

        logger.info(f"Displaying Slide {slide_no} to participants.")

        # Command Gemini to synthesize speech for the slide content
        session.generate_reply(
            instructions=f"Slide {slide_no} Text Content: {content_text}. Present this clearly."
        )

        # WAIT FOR COMPLETION:
        # Essential to wait for audio/video playback to finish before moving on.
        await session.wait_for_playout()
        
        # Buffer delay between slides for natural transitions
        await asyncio.sleep(2.0) 

    # 7. Final Handover
    session.generate_reply(instructions="Thank the audience and ask if there are any specific questions.")
    
    logger.info("Sequence Complete. Entering active standby mode.")
    
    # Keep the process alive for user questions/interaction
    await keep_alive(ctx)

if __name__ == "__main__":
    # Required for the LiveKit CLI to start the worker process
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
