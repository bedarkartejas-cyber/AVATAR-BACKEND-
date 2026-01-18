import asyncio
import logging
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

logger = logging.getLogger("avatar-agent")
logger.setLevel(logging.INFO)

async def entrypoint(ctx: JobContext):
    # Connect and subscribe to all participants (the user)
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    logger.info(f"Agent joined room: {ctx.room.name}")

    # Extract Presentation ID from metadata injected by routes.py
    await asyncio.sleep(2.0) 
    presentation_id = None
    for participant in ctx.room.participants.values():
        if participant.metadata:
            presentation_id = participant.metadata
            break

    if not presentation_id:
        logger.error("No presentation_id found. Closing session.")
        return

    # Fetch processed slides from Supabase
    slides = supabase.table("slides") \
        .select("*") \
        .eq("presentation_id", presentation_id) \
        .order("slide_number", ascending=True) \
        .execute().data

    # Initialize Brain and Visuals
    llm = create_llm()
    avatar = create_avatar()

    # SESSION CONFIG: CRITICAL FOR AVATAR VISIBILITY
    # speaking_fps=0 prevents the agent from fighting Anam for the video track.
    session = AgentSession(
        llm=llm,
        video_sampler=VoiceActivityVideoSampler(speaking_fps=0, silent_fps=0),
        preemptive_generation=False,
        min_endpointing_delay=2.0, # Buffering for Avatar lip-sync
        max_endpointing_delay=5.0,
    )

    # Start Anam session
    await avatar.start(session, room=ctx.room)

    # Begin AI Session
    await session.start(
        agent=Agent(instructions=SYSTEM_INSTRUCTIONS),
        room=ctx.room,
        room_input_options=room_io.RoomInputOptions(video_enabled=True),
    )

    # THE PRESENTATION LOOP
    for slide in slides:
        # Update frontend slide via Room Attributes
        await ctx.room.local_participant.set_attributes({
            "current_slide_url": slide["image_url"]
        })

        logger.info(f"Speaking Slide: {slide['slide_number']}")
        
        # Instruct Gemini to present this specific slide text
        session.generate_reply(
            instructions=f"Slide Content: {slide['extracted_text']}. Please present this naturally."
        )

        # Wait for the Avatar to finish speaking before moving to next slide
        await session.wait_for_playout()
        await asyncio.sleep(1.5)

    # Wrap up
    session.generate_reply(instructions="Conclude the presentation and offer to answer questions.")
    await keep_alive(ctx)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
