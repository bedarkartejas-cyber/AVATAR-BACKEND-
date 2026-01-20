import os
import logging
from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
)
from livekit.plugins import openai, simli

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simli-avatar-agent")

# ------------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------------
load_dotenv()

# ------------------------------------------------------------------
# Agent entrypoint (called by LiveKit when a room job arrives)
# ------------------------------------------------------------------
async def entrypoint(ctx: JobContext):
    logger.info(f"Job received for room: {ctx.room.name}")

    # 1️⃣ Create Agent Session (LLM brain)
    agent_session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="alloy"
        )
    )

    # 2️⃣ Create Simli Avatar
    avatar = simli.AvatarSession(
        simli_config=simli.SimliConfig(
            api_key=os.getenv("SIMLI_API_KEY"),
            face_id=os.getenv("SIMLI_FACE_ID"),
        )
    )

    # 3️⃣ START AVATAR (CORRECT SIGNATURE)
    # REQUIRED: agent_session FIRST, then room
    await avatar.start(agent_session, ctx.room)

    logger.info("Simli avatar started")

    # 4️⃣ Start agent session (audio + video come from avatar)
    await agent_session.start(
        agent=Agent(
    instructions=(
        "You are an AI mentor avatar.\n"
        "You may ONLY discuss:\n"
        "1. Python programming\n"
        "2. Machine Learning\n"
        "3. Data Science careers\n\n"
        "If asked about anything else, politely refuse.\n"
        "Use simple language and real-world examples."
    )
),
        room=ctx.room,
    )

    logger.info("Agent session started successfully")


# ------------------------------------------------------------------
# Worker bootstrap (CLI entry)
# ------------------------------------------------------------------
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint
        )
    )
