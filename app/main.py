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
from app.core.supabase import supabase  # Points to the unified core folder

# Configure logging to monitor the Agent's behavior in the terminal
logger = logging.getLogger("avatar-agent")
logger.setLevel(logging.INFO)

async def entrypoint(ctx: JobContext):
    # 1. Connect to the room and subscribe to all tracks
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    logger.info(f"Connected to room: {ctx.room.name}")

    # 2. Extract the Presentation ID from Metadata
    # We wait briefly to ensure the participant's metadata has synced
    await asyncio.sleep(1.5) 
    
    presentation_id = None
    # We iterate through participants to find the user's metadata
    for participant in ctx.room.participants.values():
        if participant.metadata:
            presentation_id = participant.metadata
            logger.info(f"Found Presentation ID: {presentation_id}")
            break

    if not presentation_id:
        logger.error("FATAL: No presentation_id found in metadata. Exiting.")
        return

    # 3. Fetch Slide Data from Supabase
    # This ensures the Agent only reads the slides you just uploaded
    slides_query = supabase.table("slides") \
        .select("*") \
        .eq("presentation_id", presentation_id) \
        .order("slide_number", ascending=True) \
        .execute()
    
    slides = slides_query.data
    if not slides:
        logger.error(f"No slides found for ID: {presentation_id}")
        return

    # 4. Initialize AI Brain (Gemini) and Avatar (Anam)
    llm = create_llm()
    avatar = create_avatar()

    session = AgentSession(
        llm=llm,
        video_sampler=VoiceActivityVideoSampler(speaking_fps=0, silent_fps=0),
        preemptive_generation=False,
        min_endpointing_delay=2.0, 
        max_endpointing_delay=5.0,
    )

    # Link the avatar to this specific session and room
    await avatar.start(session, room=ctx.room)

    # 5. Define the Presentation Persona
    # We combine your system instructions with specific presentation rules
    presenter_instructions = (
        f"{SYSTEM_INSTRUCTIONS}\n"
        "You are a professional AI presenter. "
        "I will give you slide text. Summarize it in 2-3 engaging sentences."
    )

    await session.start(
        agent=Agent(instructions=presenter_instructions),
        room=ctx.room,
        room_input_options=room_io.RoomInputOptions(video_enabled=True),
    )

    # 6. The Presentation Loop
    for slide in slides:
        slide_no = slide["slide_number"]
        image_url = slide["image_url"]
        text = slide["extracted_text"]

        # SYNC: Update the room attributes so the index.html changes the image
        await ctx.room.local_participant.set_attributes({
            "current_slide_url": image_url
        })

        logger.info(f"Presenting Slide {slide_no}...")

        # Tell the Agent to speak the slide content
        session.generate_reply(
            instructions=f"Slide {slide_no} Content: {text}. Please present this naturally."
        )

        # Wait for the audio to finish playing before moving to the next slide
        await session.wait_for_playout()
        await asyncio.sleep(1.5) 

    # 7. Conclusion
    session.generate_reply(instructions="Thank the audience and ask for questions.")
    
    # Keep the agent alive so the room doesn't close immediately
    await keep_alive(ctx)

if __name__ == "__main__":
    # Run the agent worker
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))