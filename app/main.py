# # import asyncio
# # import logging
# # import sys
# # from livekit.agents import (
# #     Agent,
# #     AgentSession,
# #     AutoSubscribe,
# #     JobContext,
# #     WorkerOptions,
# #     cli,
# # )
# # from livekit.agents.voice import VoiceActivityVideoSampler, room_io
# # from app.llm.gemini import create_llm
# # from app.avatar.anam_avatar import create_avatar
# # from app.avatar.persona import SYSTEM_INSTRUCTIONS
# # from app.utils.safety import keep_alive
# # from app.core.supabase import supabase

# # # Configure Advanced Logging for Production Monitoring
# # logging.basicConfig(level=logging.INFO)
# # logger = logging.getLogger("dia-presenter-agent")
# # logger.setLevel(logging.INFO)

# # async def entrypoint(ctx: JobContext):
# #     """
# #     Core entrypoint for the AI Agent worker. 
# #     Manages the orchestration between slides, Gemini LLM, and Anam Avatar.
# #     """
# #     logger.info(f"🚀 Initializing agent for room: {ctx.room.name}")

# #     # 1. Join Room and Auto-Subscribe to User
# #     try:
# #         await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
# #         logger.info("✅ Successfully connected to LiveKit room.")
# #     except Exception as e:
# #         logger.error(f"❌ Failed to connect to room: {e}")
# #         return

# #     # 2. Extract Session Metadata
# #     # Wait for metadata propagation and check remote_participants
# #     await asyncio.sleep(2.5) 
    
# #     presentation_id = None
# #     # Check remote participants (the human user) for the presentation_id metadata
# #     for participant in ctx.room.remote_participants.values():
# #         if participant.metadata:
# #             presentation_id = participant.metadata
# #             logger.info(f"✅ Verified Presentation ID from metadata: {presentation_id}")
# #             break

# #     if not presentation_id:
# #         logger.error("❌ FATAL: No presentation_id found in room metadata. Closing worker.")
# #         return

# #     # 3. Synchronize Slide Data from Supabase
# #     logger.info(f"🔍 Querying slide manifest for: {presentation_id}")
# #     try:
# #         # FIXED: Use desc=False instead of ascending=True for current supabase-py version
# #         query_result = supabase.table("slides") \
# #             .select("*") \
# #             .eq("presentation_id", presentation_id) \
# #             .order("slide_number", desc=False) \
# #             .execute()
        
# #         slides = query_result.data
# #         if not slides:
# #             logger.error(f"❌ Integrity Error: No slides found for presentation ID {presentation_id}")
# #             return
# #         logger.info(f"✅ Loaded {len(slides)} slides successfully.")
# #     except Exception as e:
# #         logger.error(f"❌ Supabase Query Failed: {e}")
# #         return

# #     # 4. Initialize Brain (Gemini) and Visuals (Anam)
# #     try:
# #         llm = create_llm()
# #         logger.info("✅ Gemini LLM initialized successfully.")
# #     except Exception as e:
# #         logger.error(f"❌ Failed to initialize Gemini LLM: {e}")
# #         return

# #     try:
# #         avatar = create_avatar()
# #         logger.info("✅ Anam Avatar initialized successfully.")
# #     except Exception as e:
# #         logger.error(f"❌ Failed to initialize Anam Avatar: {e}")
# #         return

# #     # 5. CONFIGURE AGENT SESSION
# #     try:
# #         session = AgentSession(
# #             llm=llm,
# #             video_sampler=VoiceActivityVideoSampler(speaking_fps=0, silent_fps=0),
# #             preemptive_generation=False,
# #             min_endpointing_delay=2.0, 
# #             max_endpointing_delay=5.0,
# #         )
# #         logger.info("✅ Agent session configured.")
# #     except Exception as e:
# #         logger.error(f"❌ Failed to configure agent session: {e}")
# #         return

# #     # Attach the Anam plugin to intercept text and convert it to avatar video
# #     try:
# #         await avatar.start(session, room=ctx.room)
# #         logger.info("✅ Anam avatar plugin attached to session.")
# #     except Exception as e:
# #         logger.error(f"❌ Failed to start avatar: {e}")
# #         return

# #     # Build presenter instructions
# #     presenter_instructions = (
# #         f"{SYSTEM_INSTRUCTIONS}\n\n"
# #         "ROLE: You are presenting a slide deck to an audience.\n"
# #         "GOAL: Present each slide's content clearly and engagingly.\n"
# #         "STRICT LIMIT: Maximum 2 sentences per response. Wait for playout before continuing.\n"
# #         "TONE: Professional, clear, and engaging."
# #     )

# #     # Start the integrated AI service
# #     try:
# #         await session.start(
# #             agent=Agent(instructions=presenter_instructions),
# #             room=ctx.room,
# #             room_input_options=room_io.RoomInputOptions(video_enabled=True),
# #         )
# #         logger.info("✅ Agent session started successfully.")
# #     except Exception as e:
# #         logger.error(f"❌ Failed to start agent session: {e}")
# #         return

# #     # 6. THE SYNCHRONIZED PRESENTATION LOOP
# #     logger.info("🎬 Starting automated presentation sequence.")
# #     for idx, slide in enumerate(slides, start=1):
# #         slide_no = slide.get("slide_number", idx)
# #         image_url = slide.get("image_url", "")
# #         content_text = slide.get("extracted_text", "")

# #         if not image_url:
# #             logger.warning(f"⚠️ Slide {slide_no} has no image URL. Skipping.")
# #             continue

# #         try:
# #             # TRIGGER FRONTEND SYNC: Update local participant attributes
# #             await ctx.room.local_participant.set_attributes({
# #                 "current_slide_url": image_url
# #             })
# #             logger.info(f"📊 Displaying Slide {slide_no}/{len(slides)} to participants.")
# #         except Exception as e:
# #             logger.error(f"❌ Failed to set slide attributes: {e}")
# #             continue

# #         try:
# #             # Command Gemini to present the slide content
# #             slide_instruction = (
# #                 f"Slide {slide_no}: {content_text}\n\n"
# #                 "Present this slide's key points clearly in 1-2 sentences."
# #             )
# #             session.generate_reply(instructions=slide_instruction)
            
# #             # WAIT FOR COMPLETION: Ensures audio/video finishes before moving to next slide
# #             await session.wait_for_playout()
# #             logger.info(f"✅ Completed presentation of slide {slide_no}.")
            
# #             # Buffer delay between slides for natural transitions
# #             await asyncio.sleep(2.0)
            
# #         except Exception as e:
# #             logger.error(f"❌ Error presenting slide {slide_no}: {e}")
# #             # Continue to next slide even if one fails
# #             continue

# #     # 7. Final Handover
# #     try:
# #         logger.info("🎉 All slides presented. Thanking audience.")
# #         session.generate_reply(
# #             instructions="Thank the audience warmly and ask if there are any questions about the presentation."
# #         )
# #         await session.wait_for_playout()
# #     except Exception as e:
# #         logger.error(f"❌ Error in final message: {e}")
    
# #     logger.info("✅ Presentation sequence complete. Entering Q&A standby mode.")
    
# #     # Keep the process alive for user interaction
# #     await keep_alive(ctx)

# # if __name__ == "__main__":
# #     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))











# import asyncio
# import logging
# import sys
# from livekit.agents import (
#     Agent,
#     AgentSession,
#     AutoSubscribe,
#     JobContext,
#     WorkerOptions,
#     cli,
# )
# from livekit.agents.voice import VoiceActivityVideoSampler, room_io
# from app.llm.gemini import create_llm
# from app.avatar.anam_avatar import create_avatar
# from app.avatar.persona import SYSTEM_INSTRUCTIONS
# from app.utils.safety import keep_alive
# from app.core.supabase import supabase

# # Configure Advanced Logging for Production Monitoring
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("dia-presenter-agent")
# logger.setLevel(logging.INFO)

# async def entrypoint(ctx: JobContext):
#     """
#     Core entrypoint for the AI Agent worker. 
#     Manages the orchestration between slides, Gemini LLM, and Anam Avatar.
#     """
#     logger.info(f"🚀 Initializing agent for room: {ctx.room.name}")

#     # 1. Join Room and Auto-Subscribe to User
#     try:
#         await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
#         logger.info("✅ Successfully connected to LiveKit room.")
#     except Exception as e:
#         logger.error(f"❌ Failed to connect to room: {e}")
#         return

#     # 2. Extract Session Metadata
#     # Wait for metadata propagation and check remote_participants
#     await asyncio.sleep(2.5) 
    
#     presentation_id = None
#     # Check remote participants (the human user) for the presentation_id metadata
#     for participant in ctx.room.remote_participants.values():
#         if participant.metadata:
#             presentation_id = participant.metadata
#             logger.info(f"✅ Verified Presentation ID from metadata: {presentation_id}")
#             break

#     if not presentation_id:
#         logger.error("❌ FATAL: No presentation_id found in room metadata. Closing worker.")
#         return

#     # 3. Synchronize Slide Data from Supabase
#     logger.info(f"🔍 Querying slide manifest for: {presentation_id}")
#     try:
#         query_result = supabase.table("slides") \
#             .select("*") \
#             .eq("presentation_id", presentation_id) \
#             .order("slide_number", desc=False) \
#             .execute()
        
#         slides = query_result.data
#         if not slides:
#             logger.error(f"❌ Integrity Error: No slides found for presentation ID {presentation_id}")
#             return
#         logger.info(f"✅ Loaded {len(slides)} slides successfully.")
#     except Exception as e:
#         logger.error(f"❌ Supabase Query Failed: {e}")
#         return

#     # 4. Initialize Brain (Gemini) and Visuals (Anam)
#     try:
#         llm = create_llm()
#         logger.info("✅ Gemini LLM initialized successfully.")
#     except Exception as e:
#         logger.error(f"❌ Failed to initialize Gemini LLM: {e}")
#         return

#     try:
#         avatar = create_avatar()
#         logger.info("✅ Anam Avatar initialized successfully.")
#     except Exception as e:
#         logger.error(f"❌ Failed to initialize Anam Avatar: {e}")
#         return

#     # 5. CONFIGURE AGENT SESSION
#     try:
#         session = AgentSession(
#             llm=llm,
#             video_sampler=VoiceActivityVideoSampler(speaking_fps=0, silent_fps=0),
#             preemptive_generation=False,
#             min_endpointing_delay=2.0, 
#             max_endpointing_delay=5.0,
#         )
#         logger.info("✅ Agent session configured.")
#     except Exception as e:
#         logger.error(f"❌ Failed to configure agent session: {e}")
#         return

#     # Attach the Anam plugin to intercept text and convert it to avatar video
#     try:
#         await avatar.start(session, room=ctx.room)
#         logger.info("✅ Anam avatar plugin attached to session.")
#     except Exception as e:
#         logger.error(f"❌ Failed to start avatar: {e}")
#         return

#     # Build presenter instructions
#     presenter_instructions = (
#         f"{SYSTEM_INSTRUCTIONS}\n\n"
#         "ROLE: You are presenting a slide deck to an audience.\n"
#         "GOAL: Present each slide's content clearly and engagingly.\n"
#         "STRICT LIMIT: Maximum 2 sentences per response. Wait for playout before continuing.\n"
#         "TONE: Professional, clear, and engaging."
#     )

#     # Start the integrated AI service
#     try:
#         await session.start(
#             agent=Agent(instructions=presenter_instructions),
#             room=ctx.room,
#             room_input_options=room_io.RoomInputOptions(video_enabled=True),
#         )
#         logger.info("✅ Agent session started successfully.")
#     except Exception as e:
#         logger.error(f"❌ Failed to start agent session: {e}")
#         return

#     # 6. THE SYNCHRONIZED PRESENTATION LOOP
#     logger.info("🎬 Starting automated presentation sequence.")
    
#     # CRITICAL: Track speech handles to ensure sequential presentation
#     for idx, slide in enumerate(slides, start=1):
#         slide_no = slide.get("slide_number", idx)
#         image_url = slide.get("image_url", "")
#         content_text = slide.get("extracted_text", "")

#         if not image_url:
#             logger.warning(f"⚠️ Slide {slide_no} has no image URL. Skipping.")
#             continue

#         try:
#             # TRIGGER FRONTEND SYNC: Update local participant attributes
#             await ctx.room.local_participant.set_attributes({
#                 "current_slide_url": image_url
#             })
#             logger.info(f"📊 Displaying Slide {slide_no}/{len(slides)} to participants.")
#         except Exception as e:
#             logger.error(f"❌ Failed to set slide attributes: {e}")
#             continue

#         try:
#             # Command Gemini to present the slide content
#             slide_instruction = (
#                 f"Slide {slide_no}: {content_text}\n\n"
#                 "Present this slide's key points clearly in 1-2 sentences."
#             )
            
#             # FIXED: Use generate_reply() for realtime models
#             # This returns a SpeechHandle that we can await
#             speech_handle = session.generate_reply(instructions=slide_instruction)
            
#             # Wait for the current speech to be ready (generation complete)
#             await speech_handle.wait_for_next_playout()
            
#             logger.info(f"✅ Completed presentation of slide {slide_no}.")
            
#             # Buffer delay between slides for natural transitions
#             await asyncio.sleep(2.0)
            
#         except Exception as e:
#             logger.error(f"❌ Error presenting slide {slide_no}: {e}")
#             # Continue to next slide even if one fails
#             continue

#     # 7. Final Handover
#     try:
#         logger.info("🎉 All slides presented. Thanking audience.")
#         final_speech = session.generate_reply(
#             instructions="Thank you for your attention! I'd be happy to answer any questions you may have about this presentation."
#         )
#         await final_speech.wait_for_next_playout()
#     except Exception as e:
#         logger.error(f"❌ Error in final message: {e}")
    
#     logger.info("✅ Presentation sequence complete. Entering Q&A standby mode.")
    
#     # Keep the process alive for user interaction
#     await keep_alive(ctx)

# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))






import asyncio
import logging
from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.agents.voice import VoiceActivityVideoSampler, room_io
from app.llm.gemini import create_llm
from app.avatar.anam_avatar import create_avatar
from app.avatar.persona import SYSTEM_INSTRUCTIONS
from app.utils.safety import keep_alive
from app.core.supabase import supabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dia-presenter-agent")
logger.setLevel(logging.INFO)

# Global state for presentation control
current_slide_index = 0
slides_data = []
total_slides = 0
room_context = None

async def entrypoint(ctx: JobContext):
    global current_slide_index, slides_data, total_slides, room_context
    
    logger.info(f"🚀 Initializing agent for room: {ctx.room.name}")
    room_context = ctx  # Store for use in navigation functions

    # 1. Connect to room
    try:
        await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
        logger.info("✅ Successfully connected to LiveKit room.")
    except Exception as e:
        logger.error(f"❌ Failed to connect to room: {e}")
        return

    # 2. Get presentation ID from metadata
    await asyncio.sleep(2.5) 
    
    presentation_id = None
    for participant in ctx.room.remote_participants.values():
        if participant.metadata:
            presentation_id = participant.metadata
            logger.info(f"✅ Verified Presentation ID: {presentation_id}")
            break

    if not presentation_id:
        logger.error("❌ FATAL: No presentation_id found")
        return

    # 3. Load slides from Supabase
    logger.info(f"🔍 Querying slides for: {presentation_id}")
    try:
        query_result = supabase.table("slides") \
            .select("*") \
            .eq("presentation_id", presentation_id) \
            .order("slide_number", desc=False) \
            .execute()
        
        slides_data = query_result.data
        total_slides = len(slides_data)
        
        if not slides_data:
            logger.error(f"❌ No slides found for {presentation_id}")
            return
        logger.info(f"✅ Loaded {total_slides} slides")
    except Exception as e:
        logger.error(f"❌ Supabase query failed: {e}")
        return

    # 4. Initialize LLM and Avatar
    try:
        llm_model = create_llm()
        logger.info("✅ Gemini LLM initialized")
    except Exception as e:
        logger.error(f"❌ Failed to init LLM: {e}")
        return

    try:
        avatar = create_avatar()
        logger.info("✅ Anam Avatar initialized")
    except Exception as e:
        logger.error(f"❌ Failed to init Avatar: {e}")
        return

    # 5. Configure Agent Session
    try:
        session = AgentSession(
            llm=llm_model,
            video_sampler=VoiceActivityVideoSampler(speaking_fps=0, silent_fps=0),
            preemptive_generation=False,
            min_endpointing_delay=1.5, 
            max_endpointing_delay=3.0,
        )
        logger.info("✅ Agent session configured")
    except Exception as e:
        logger.error(f"❌ Failed to configure session: {e}")
        return

    # Attach avatar
    try:
        await avatar.start(session, room=ctx.room)
        logger.info("✅ Anam avatar attached")
    except Exception as e:
        logger.error(f"❌ Failed to start avatar: {e}")
        return

    # Build instructions
    presenter_instructions = (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        "ROLE: You are an AI presenter for a slide deck.\n"
        "CAPABILITIES:\n"
        "- Present slide content clearly and concisely\n"
        "- Navigate slides using next_slide, previous_slide, and goto_slide tools\n"
        "- Respond to user commands like 'next', 'previous', 'go back', 'go to slide 3'\n"
        "\n"
        "RULES:\n"
        "1. When user says 'next' or similar → call next_slide()\n"
        "2. When user says 'previous' or 'back' → call previous_slide()\n"
        "3. When user says 'go to slide X' → call goto_slide(X)\n"
        "4. Keep responses brief (1-2 sentences)\n"
        "5. After navigating, briefly mention what's on the new slide\n"
        "\n"
        "TONE: Professional, clear, and engaging."
    )

    # Start session with tools
    try:
        await session.start(
            agent=Agent(
                instructions=presenter_instructions,
                tools=[next_slide, previous_slide, goto_slide]
            ),
            room=ctx.room,
            room_input_options=room_io.RoomInputOptions(video_enabled=True),
        )
        logger.info("✅ Agent session started with navigation tools")
    except Exception as e:
        logger.error(f"❌ Failed to start session: {e}")
        return

    # 6. Send initial slide data to frontend
    logger.info("📤 Sending initial slide to frontend...")
    try:
        await ctx.room.local_participant.set_attributes({
            "total_slides": str(total_slides),
            "current_slide_index": "0",
            "presentation_status": "ready"
        })
        logger.info(f"✅ Sent metadata to frontend")
    except Exception as e:
        logger.error(f"❌ Failed to send metadata: {e}")

    await asyncio.sleep(2.0)

    # 7. Present first slide automatically
    logger.info("🎬 Starting presentation...")
    
    try:
        await update_slide_display()
        
        # Present first slide
        first_slide = slides_data[0]
        content = first_slide.get("extracted_text", "")
        
        logger.info(f"🎤 Presenting slide 1...")
        # Just say the instruction, don't await speech - let it play naturally
        session.say(
            f"Welcome! Let's begin. Here's the first slide: {content}. Present this briefly in 1-2 sentences.",
            allow_interruptions=True
        )
        
        logger.info(f"✅ Initiated slide 1 presentation")
        
    except Exception as e:
        logger.error(f"❌ Error in initial presentation: {e}")
    
    # 8. Enter interactive mode
    logger.info("✅ Presentation ready. Listening for voice commands (next, previous, etc.)")
    await ctx.room.local_participant.set_attributes({
        "presentation_status": "interactive"
    })
    
    # Keep alive
    await keep_alive(ctx)


# ==================== NAVIGATION TOOL FUNCTIONS ====================

@function_tool(description="Move to the next slide in the presentation")
async def next_slide():
    """Move to the next slide when user says 'next', 'next slide', or 'move forward'"""
    global current_slide_index, total_slides
    
    if current_slide_index < total_slides - 1:
        current_slide_index += 1
        await update_slide_display()
        
        # Get new slide content
        slide = slides_data[current_slide_index]
        content = slide.get("extracted_text", "")
        
        logger.info(f"✅ Moved to slide {current_slide_index + 1}")
        return f"Now on slide {current_slide_index + 1} of {total_slides}. {content[:100]}"
    else:
        logger.info("Already on last slide")
        return "Already on the last slide"


@function_tool(description="Move to the previous slide in the presentation")
async def previous_slide():
    """Move to the previous slide when user says 'previous', 'back', or 'go back'"""
    global current_slide_index, total_slides
    
    if current_slide_index > 0:
        current_slide_index -= 1
        await update_slide_display()
        
        # Get new slide content
        slide = slides_data[current_slide_index]
        content = slide.get("extracted_text", "")
        
        logger.info(f"✅ Moved to slide {current_slide_index + 1}")
        return f"Now on slide {current_slide_index + 1} of {total_slides}. {content[:100]}"
    else:
        logger.info("Already on first slide")
        return "Already on the first slide"


@function_tool(description="Jump to a specific slide number when user says 'go to slide X' or 'show slide X'")
async def goto_slide(slide_number: int):
    """
    Jump to a specific slide
    
    Args:
        slide_number: The slide number to jump to (1-indexed)
    """
    global current_slide_index, total_slides
    
    if 1 <= slide_number <= total_slides:
        current_slide_index = slide_number - 1
        await update_slide_display()
        
        # Get new slide content
        slide = slides_data[current_slide_index]
        content = slide.get("extracted_text", "")
        
        logger.info(f"✅ Jumped to slide {slide_number}")
        return f"Now on slide {slide_number} of {total_slides}. {content[:100]}"
    else:
        logger.warning(f"Invalid slide number: {slide_number}")
        return f"Invalid slide number. Please choose between 1 and {total_slides}"


async def update_slide_display():
    """Update the frontend to show the current slide"""
    global current_slide_index, total_slides, room_context
    
    if room_context is None:
        logger.error("❌ Room context not available")
        return
    
    try:
        await room_context.room.local_participant.set_attributes({
            "current_slide_index": str(current_slide_index),
            "total_slides": str(total_slides),
            "presentation_status": "interactive"
        })
        logger.info(f"📊 Display updated: Slide {current_slide_index + 1}/{total_slides}")
    except Exception as e:
        logger.error(f"❌ Failed to update display: {e}")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
