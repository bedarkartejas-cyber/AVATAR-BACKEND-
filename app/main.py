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






# import asyncio
# import logging
# from livekit.agents import (
#     Agent,
#     AgentSession,
#     AutoSubscribe,
#     JobContext,
#     WorkerOptions,
#     cli,
#     function_tool,
# )
# from livekit.agents.voice import VoiceActivityVideoSampler, room_io
# from app.llm.gemini import create_llm
# from app.avatar.anam_avatar import create_avatar
# from app.avatar.persona import SYSTEM_INSTRUCTIONS
# from app.utils.safety import keep_alive
# from app.core.supabase import supabase

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("dia-presenter-agent")
# logger.setLevel(logging.INFO)

# # Global state for presentation control
# current_slide_index = 0
# slides_data = []
# total_slides = 0
# room_context = None

# async def entrypoint(ctx: JobContext):
#     global current_slide_index, slides_data, total_slides, room_context
    
#     logger.info(f"🚀 Initializing agent for room: {ctx.room.name}")
#     room_context = ctx  # Store for use in navigation functions

#     # 1. Connect to room
#     try:
#         await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
#         logger.info("✅ Successfully connected to LiveKit room.")
#     except Exception as e:
#         logger.error(f"❌ Failed to connect to room: {e}")
#         return

#     # 2. Get presentation ID from metadata
#     await asyncio.sleep(2.5) 
    
#     presentation_id = None
#     for participant in ctx.room.remote_participants.values():
#         if participant.metadata:
#             presentation_id = participant.metadata
#             logger.info(f"✅ Verified Presentation ID: {presentation_id}")
#             break

#     if not presentation_id:
#         logger.error("❌ FATAL: No presentation_id found")
#         return

#     # 3. Load slides from Supabase
#     logger.info(f"🔍 Querying slides for: {presentation_id}")
#     try:
#         query_result = supabase.table("slides") \
#             .select("*") \
#             .eq("presentation_id", presentation_id) \
#             .order("slide_number", desc=False) \
#             .execute()
        
#         slides_data = query_result.data
#         total_slides = len(slides_data)
        
#         if not slides_data:
#             logger.error(f"❌ No slides found for {presentation_id}")
#             return
#         logger.info(f"✅ Loaded {total_slides} slides")
#     except Exception as e:
#         logger.error(f"❌ Supabase query failed: {e}")
#         return

#     # 4. Initialize LLM and Avatar
#     try:
#         llm_model = create_llm()
#         logger.info("✅ Gemini LLM initialized")
#     except Exception as e:
#         logger.error(f"❌ Failed to init LLM: {e}")
#         return

#     try:
#         avatar = create_avatar()
#         logger.info("✅ Anam Avatar initialized")
#     except Exception as e:
#         logger.error(f"❌ Failed to init Avatar: {e}")
#         return

#     # 5. Configure Agent Session
#     try:
#         session = AgentSession(
#             llm=llm_model,
#             video_sampler=VoiceActivityVideoSampler(speaking_fps=0, silent_fps=0),
#             preemptive_generation=False,
#             min_endpointing_delay=1.5, 
#             max_endpointing_delay=3.0,
#         )
#         logger.info("✅ Agent session configured")
#     except Exception as e:
#         logger.error(f"❌ Failed to configure session: {e}")
#         return

#     # Attach avatar
#     try:
#         await avatar.start(session, room=ctx.room)
#         logger.info("✅ Anam avatar attached")
#     except Exception as e:
#         logger.error(f"❌ Failed to start avatar: {e}")
#         return

#     # Build instructions
#     presenter_instructions = (
#         f"{SYSTEM_INSTRUCTIONS}\n\n"
#         "ROLE: You are an AI presenter for a slide deck.\n"
#         "CAPABILITIES:\n"
#         "- Present slide content clearly and concisely\n"
#         "- Navigate slides using next_slide, previous_slide, and goto_slide tools\n"
#         "- Respond to user commands like 'next', 'previous', 'go back', 'go to slide 3'\n"
#         "\n"
#         "RULES:\n"
#         "1. When user says 'next' or similar → call next_slide()\n"
#         "2. When user says 'previous' or 'back' → call previous_slide()\n"
#         "3. When user says 'go to slide X' → call goto_slide(X)\n"
#         "4. Keep responses brief (1-2 sentences)\n"
#         "5. After navigating, briefly mention what's on the new slide\n"
#         "\n"
#         "TONE: Professional, clear, and engaging."
#     )

#     # Start session with tools
#     try:
#         await session.start(
#             agent=Agent(
#                 instructions=presenter_instructions,
#                 tools=[next_slide, previous_slide, goto_slide]
#             ),
#             room=ctx.room,
#             room_input_options=room_io.RoomInputOptions(video_enabled=True),
#         )
#         logger.info("✅ Agent session started with navigation tools")
#     except Exception as e:
#         logger.error(f"❌ Failed to start session: {e}")
#         return

#     # 6. Send initial slide data to frontend
#     logger.info("📤 Sending initial slide to frontend...")
#     try:
#         await ctx.room.local_participant.set_attributes({
#             "total_slides": str(total_slides),
#             "current_slide_index": "0",
#             "presentation_status": "ready"
#         })
#         logger.info(f"✅ Sent metadata to frontend")
#     except Exception as e:
#         logger.error(f"❌ Failed to send metadata: {e}")

#     await asyncio.sleep(2.0)

#     # 7. Present first slide automatically
#     logger.info("🎬 Starting presentation...")
    
#     try:
#         await update_slide_display()
        
#         # Present first slide
#         first_slide = slides_data[0]
#         content = first_slide.get("extracted_text", "")
        
#         logger.info(f"🎤 Presenting slide 1...")
#         # Just say the instruction, don't await speech - let it play naturally
#         session.say(
#             f"Welcome! Let's begin. Here's the first slide: {content}. Present this briefly in 1-2 sentences.",
#             allow_interruptions=True
#         )
        
#         logger.info(f"✅ Initiated slide 1 presentation")
        
#     except Exception as e:
#         logger.error(f"❌ Error in initial presentation: {e}")
    
#     # 8. Enter interactive mode
#     logger.info("✅ Presentation ready. Listening for voice commands (next, previous, etc.)")
#     await ctx.room.local_participant.set_attributes({
#         "presentation_status": "interactive"
#     })
    
#     # Keep alive
#     await keep_alive(ctx)


# # ==================== NAVIGATION TOOL FUNCTIONS ====================

# @function_tool(description="Move to the next slide in the presentation")
# async def next_slide():
#     """Move to the next slide when user says 'next', 'next slide', or 'move forward'"""
#     global current_slide_index, total_slides
    
#     if current_slide_index < total_slides - 1:
#         current_slide_index += 1
#         await update_slide_display()
        
#         # Get new slide content
#         slide = slides_data[current_slide_index]
#         content = slide.get("extracted_text", "")
        
#         logger.info(f"✅ Moved to slide {current_slide_index + 1}")
#         return f"Now on slide {current_slide_index + 1} of {total_slides}. {content[:100]}"
#     else:
#         logger.info("Already on last slide")
#         return "Already on the last slide"


# @function_tool(description="Move to the previous slide in the presentation")
# async def previous_slide():
#     """Move to the previous slide when user says 'previous', 'back', or 'go back'"""
#     global current_slide_index, total_slides
    
#     if current_slide_index > 0:
#         current_slide_index -= 1
#         await update_slide_display()
        
#         # Get new slide content
#         slide = slides_data[current_slide_index]
#         content = slide.get("extracted_text", "")
        
#         logger.info(f"✅ Moved to slide {current_slide_index + 1}")
#         return f"Now on slide {current_slide_index + 1} of {total_slides}. {content[:100]}"
#     else:
#         logger.info("Already on first slide")
#         return "Already on the first slide"


# @function_tool(description="Jump to a specific slide number when user says 'go to slide X' or 'show slide X'")
# async def goto_slide(slide_number: int):
#     """
#     Jump to a specific slide
    
#     Args:
#         slide_number: The slide number to jump to (1-indexed)
#     """
#     global current_slide_index, total_slides
    
#     if 1 <= slide_number <= total_slides:
#         current_slide_index = slide_number - 1
#         await update_slide_display()
        
#         # Get new slide content
#         slide = slides_data[current_slide_index]
#         content = slide.get("extracted_text", "")
        
#         logger.info(f"✅ Jumped to slide {slide_number}")
#         return f"Now on slide {slide_number} of {total_slides}. {content[:100]}"
#     else:
#         logger.warning(f"Invalid slide number: {slide_number}")
#         return f"Invalid slide number. Please choose between 1 and {total_slides}"


# async def update_slide_display():
#     """Update the frontend to show the current slide"""
#     global current_slide_index, total_slides, room_context
    
#     if room_context is None:
#         logger.error("❌ Room context not available")
#         return
    
#     try:
#         await room_context.room.local_participant.set_attributes({
#             "current_slide_index": str(current_slide_index),
#             "total_slides": str(total_slides),
#             "presentation_status": "interactive"
#         })
#         logger.info(f"📊 Display updated: Slide {current_slide_index + 1}/{total_slides}")
#     except Exception as e:
#         logger.error(f"❌ Failed to update display: {e}")


# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))



















# import asyncio
# import logging
# from livekit.agents import (
#     Agent,
#     AgentSession,
#     AutoSubscribe,
#     JobContext,
#     WorkerOptions,
#     cli,
#     function_tool,
# )
# from livekit.agents.voice import VoiceActivityVideoSampler, room_io
# from app.llm.gemini import create_llm
# from app.avatar.anam_avatar import create_avatar
# from app.avatar.persona import SYSTEM_INSTRUCTIONS
# from app.utils.safety import keep_alive
# from app.core.supabase import supabase

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("dia-presenter-agent")
# logger.setLevel(logging.INFO)

# # Global state for presentation control
# current_slide_index = 0
# slides_data = []
# total_slides = 0
# room_context = None

# async def entrypoint(ctx: JobContext):
#     global current_slide_index, slides_data, total_slides, room_context
    
#     logger.info(f"🚀 Initializing agent for room: {ctx.room.name}")
#     room_context = ctx  # Store for use in navigation functions

#     # 1. Connect to room
#     try:
#         await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
#         logger.info("✅ Successfully connected to LiveKit room.")
#     except Exception as e:
#         logger.error(f"❌ Failed to connect to room: {e}")
#         return

#     # 2. Get presentation ID from metadata
#     await asyncio.sleep(2.5) 
    
#     presentation_id = None
#     for participant in ctx.room.remote_participants.values():
#         if participant.metadata:
#             presentation_id = participant.metadata
#             logger.info(f"✅ Verified Presentation ID: {presentation_id}")
#             break

#     if not presentation_id:
#         logger.error("❌ FATAL: No presentation_id found")
#         return

#     # 3. Load slides from Supabase
#     logger.info(f"🔍 Querying slides for: {presentation_id}")
#     try:
#         query_result = supabase.table("slides") \
#             .select("*") \
#             .eq("presentation_id", presentation_id) \
#             .order("slide_number", desc=False) \
#             .execute()
        
#         slides_data = query_result.data
#         total_slides = len(slides_data)
        
#         if not slides_data:
#             logger.error(f"❌ No slides found for {presentation_id}")
#             return
#         logger.info(f"✅ Loaded {total_slides} slides")
#     except Exception as e:
#         logger.error(f"❌ Supabase query failed: {e}")
#         return

#     # 4. Initialize LLM and Avatar
#     try:
#         llm_model = create_llm()
#         logger.info("✅ Gemini LLM initialized")
#     except Exception as e:
#         logger.error(f"❌ Failed to init LLM: {e}")
#         return

#     try:
#         avatar = create_avatar()
#         logger.info("✅ Anam Avatar initialized")
#     except Exception as e:
#         logger.error(f"❌ Failed to init Avatar: {e}")
#         return

#     # 5. Configure Agent Session with enhanced stability settings
#     try:
#         session = AgentSession(
#             llm=llm_model,
#             video_sampler=VoiceActivityVideoSampler(speaking_fps=0, silent_fps=0),
#             preemptive_generation=False,
#             # IMPROVEMENT: Increased delay to handle network jitter and ensure 
#             # the user is fully done speaking before the agent interrupts
#             min_endpointing_delay=2.0, 
#             max_endpointing_delay=4.0,
#         )
        
#         # IMPROVEMENT: Manually increase the RPC timeout for the local participant 
#         # to prevent "failed to perform clear buffer rpc" Connection Timeouts
#         if hasattr(ctx.room.local_participant, 'rpc_timeout'):
#             ctx.room.local_participant.rpc_timeout = 15.0
            
#         logger.info("✅ Agent session configured with stability updates")
#     except Exception as e:
#         logger.error(f"❌ Failed to configure session: {e}")
#         return

#     # Attach avatar
#     try:
#         await avatar.start(session, room=ctx.room)
#         logger.info("✅ Anam avatar attached")
#     except Exception as e:
#         logger.error(f"❌ Failed to start avatar: {e}")
#         return

#     # 6. Start session with tools
#     try:
#         await session.start(
#             agent=Agent(
#                 instructions=SYSTEM_INSTRUCTIONS,
#                 tools=[next_slide, previous_slide, goto_slide]
#             ),
#             room=ctx.room,
#             # IMPROVEMENT: Ensure the agent stays alive even if there are 
#             # minor stream flickers or brief disconnects
#             room_input_options=room_io.RoomInputOptions(
#                 video_enabled=True,
#                 close_on_disconnect=True # Set to False if you want agent to persist
#             ),
#         )
#         logger.info("✅ Agent session started with navigation tools")
#     except Exception as e:
#         logger.error(f"❌ Failed to start session: {e}")
#         return

#     # 7. Send initial slide data to frontend
#     logger.info("📤 Sending initial slide to frontend...")
#     try:
#         await ctx.room.local_participant.set_attributes({
#             "total_slides": str(total_slides),
#             "current_slide_index": "0",
#             "presentation_status": "interactive"
#         })
#         logger.info(f"✅ Sent metadata to frontend")
#     except Exception as e:
#         logger.error(f"❌ Failed to send metadata: {e}")

#     await asyncio.sleep(2.0)
    
#     # 8. Display first slide
#     try:
#         await update_slide_display()
#         logger.info("✅ First slide display updated.")
        
#         # Get first slide content
#         first_slide = slides_data[0]
#         content = first_slide.get("extracted_text", "")
        
#         # Push first slide content to the session so Dia starts talking immediately
#         session.push_context(
#             f"INITIAL SLIDE CONTENT:\n{content}\n\n"
#             "Please introduce yourself briefly as Dia and present this first slide. "
#             "Remember to end by asking if you can move to the next slide."
#         )
#         logger.info("🎙️ Dia is now presenting the first slide.")
        
#     except Exception as e:
#         logger.error(f"❌ Error starting first slide presentation: {e}")
    
#     # 9. Enter interactive mode
#     logger.info("✅ Presentation ready. Listening for voice commands.")
    
#     # Keep alive logic
#     await keep_alive(ctx)


# # ==================== NAVIGATION TOOL FUNCTIONS ====================

# @function_tool(description="Move to the next slide in the presentation")
# async def next_slide():
#     """Move to the next slide when user says 'next', 'next slide', or 'move forward'"""
#     global current_slide_index, total_slides
    
#     if current_slide_index < total_slides - 1:
#         current_slide_index += 1
#         await update_slide_display()
        
#         slide = slides_data[current_slide_index]
#         content = slide.get("extracted_text", "")
        
#         logger.info(f"✅ Moved to slide {current_slide_index + 1}")
        
#         return f"SLIDE CONTENT:\n{content}\n\nPresent the key points from this slide in 2-3 sentences using professional Indian English."
#     else:
#         logger.info("Already on last slide")
#         return "This is the final slide. We've completed the presentation."


# @function_tool(description="Move to the previous slide in the presentation")
# async def previous_slide():
#     """Move to the previous slide when user says 'previous', 'back', or 'go back'"""
#     global current_slide_index, total_slides
    
#     if current_slide_index > 0:
#         current_slide_index -= 1
#         await update_slide_display()
        
#         slide = slides_data[current_slide_index]
#         content = slide.get("extracted_text", "")
        
#         logger.info(f"✅ Moved to slide {current_slide_index + 1}")
        
#         return f"SLIDE CONTENT:\n{content}\n\nPresent the key points from this slide in 2-3 sentences using professional Indian English."
#     else:
#         logger.info("Already on first slide")
#         return "We're already on the first slide."


# @function_tool(description="Jump to a specific slide number when user says 'go to slide X' or 'show slide X'")
# async def goto_slide(slide_number: int):
#     """Jump to a specific slide"""
#     global current_slide_index, total_slides
    
#     if 1 <= slide_number <= total_slides:
#         current_slide_index = slide_number - 1
#         await update_slide_display()
        
#         slide = slides_data[current_slide_index]
#         content = slide.get("extracted_text", "")
        
#         logger.info(f"✅ Jumped to slide {slide_number}")
        
#         return f"SLIDE CONTENT:\n{content}\n\nPresent the key points from this slide in 2-3 sentences using professional Indian English."
#     else:
#         logger.warning(f"Invalid slide number: {slide_number}")
#         return f"Please choose a slide number between 1 and {total_slides}."


# async def update_slide_display():
#     """Update the frontend via room attributes to show the current slide"""
#     global current_slide_index, total_slides, room_context
    
#     if room_context is None:
#         logger.error("❌ Room context not available")
#         return
    
#     try:
#         await room_context.room.local_participant.set_attributes({
#             "current_slide_index": str(current_slide_index),
#             "total_slides": str(total_slides),
#             "presentation_status": "interactive"
#         })
#         logger.info(f"📊 Display updated: Slide {current_slide_index + 1}/{total_slides}")
#     except Exception as e:
#         logger.error(f"❌ Failed to update display: {e}")


# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))



































# import asyncio
# import logging
# from livekit.agents import (
#     Agent,
#     AgentSession,
#     AutoSubscribe,
#     JobContext,
#     WorkerOptions,
#     cli,
#     function_tool,
# )
# from livekit.agents.voice import VoiceActivityVideoSampler, room_io
# from app.llm.gemini import create_llm
# from app.avatar.anam_avatar import create_avatar
# from app.avatar.persona import SYSTEM_INSTRUCTIONS
# from app.utils.safety import keep_alive
# from app.core.supabase import supabase

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("dia-presenter-agent")
# logger.setLevel(logging.INFO)

# # Global state for presentation control
# current_slide_index = 0
# slides_data = []
# total_slides = 0
# room_context = None
# agent_instance = None
# session = None
# avatar = None

# async def entrypoint(ctx: JobContext):
#     global current_slide_index, slides_data, total_slides, room_context, agent_instance, session, avatar
    
#     logger.info(f"🚀 Initializing agent for room: {ctx.room.name}")
#     room_context = ctx

#     # 1. Connect to room
#     try:
#         await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
#         logger.info("✅ Successfully connected to LiveKit room.")
#     except Exception as e:
#         logger.error(f"❌ Failed to connect to room: {e}")
#         return

#     # 2. Get presentation ID from metadata
#     await asyncio.sleep(2.5) 
    
#     presentation_id = None
#     for participant in ctx.room.remote_participants.values():
#         if participant.metadata:
#             presentation_id = participant.metadata
#             logger.info(f"✅ Verified Presentation ID: {presentation_id}")
#             break

#     if not presentation_id:
#         logger.error("❌ FATAL: No presentation_id found")
#         return

#     # 3. Load slides from Supabase
#     logger.info(f"🔍 Querying slides for: {presentation_id}")
#     try:
#         query_result = supabase.table("slides") \
#             .select("*") \
#             .eq("presentation_id", presentation_id) \
#             .order("slide_number", desc=False) \
#             .execute()
        
#         slides_data = query_result.data
#         total_slides = len(slides_data)
        
#         if not slides_data:
#             logger.error(f"❌ No slides found for {presentation_id}")
#             return
#         logger.info(f"✅ Loaded {total_slides} slides")
#     except Exception as e:
#         logger.error(f"❌ Supabase query failed: {e}")
#         return

#     # 4. Initialize LLM and Avatar
#     try:
#         llm_model = create_llm()
#         logger.info("✅ Gemini LLM initialized")
#     except Exception as e:
#         logger.error(f"❌ Failed to init LLM: {e}")
#         return

#     try:
#         avatar = create_avatar()
#         logger.info("✅ Anam Avatar initialized")
#     except Exception as e:
#         logger.error(f"❌ Failed to init Avatar: {e}")
#         return

#     # 5. Create initial Agent with comprehensive instructions
#     first_slide = slides_data[0]
#     first_content = first_slide.get("extracted_text", "")
    
#     initial_instructions = f"""{SYSTEM_INSTRUCTIONS}

# YOU ARE DIA, A PROFESSIONAL PRESENTATION ASSISTANT.

# CURRENT TASK: PRESENT THE FIRST SLIDE

# SLIDE CONTENT:
# {first_content}

# IMPORTANT INSTRUCTIONS:
# 1. Start by introducing yourself: "Hello, I'm Dia, your presentation assistant."
# 2. Present this first slide's key points in 2-3 sentences using professional Indian English.
# 3. Speak clearly and at a moderate pace.
# 4. End by saying: "Shall we move to the next slide?"
# 5. After presenting, wait for the user's response.

# DO NOT:
# - Rush through the content
# - Speak too fast
# - Skip the introduction
# - Forget to ask about moving to the next slide

# BEGIN YOUR PRESENTATION NOW."""

#     try:
#         agent_instance = Agent(
#             instructions=initial_instructions,
#             tools=[next_slide, previous_slide, goto_slide]
#         )
#         logger.info("✅ Agent instance created with comprehensive instructions")
#     except Exception as e:
#         logger.error(f"❌ Failed to create Agent: {e}")
#         return

#     # 6. Configure Agent Session with optimized stability settings
#     try:
#         session = AgentSession(
#             llm=llm_model,
#             video_sampler=VoiceActivityVideoSampler(speaking_fps=0, silent_fps=0),
#             preemptive_generation=False,
#             min_endpointing_delay=2.0,  # Increased for better stability
#             max_endpointing_delay=4.0,
#             resume_false_interruption=False,  # Prevents channel errors
#         )
        
#         logger.info("✅ Agent session configured with optimized settings")
#     except Exception as e:
#         logger.error(f"❌ Failed to configure session: {e}")
#         return

#     # Attach avatar
#     try:
#         await avatar.start(session, room=ctx.room)
#         logger.info("✅ Anam avatar attached")
#     except Exception as e:
#         logger.error(f"❌ Failed to start avatar: {e}")
#         return

#     # 7. Start session with the agent
#     try:
#         await session.start(
#             agent=agent_instance,
#             room=ctx.room,
#             room_input_options=room_io.RoomInputOptions(
#                 video_enabled=True,
#                 close_on_disconnect=False,
#                 audio_enabled=True,
#             ),
#         )
#         logger.info("✅ Agent session started successfully")
#     except Exception as e:
#         logger.error(f"❌ Failed to start session: {e}")
#         return

#     # 8. Set up transcription handler to fix "no handler for topic lk.transcription"
#     try:
#         # Register a handler for transcription messages
#         async def handle_transcription(data: str):
#             logger.debug(f"📝 Transcription received: {data[:100]}...")
        
#         # Get the participant to set up data stream
#         local_participant = ctx.room.local_participant
#         if local_participant:
#             # Set up data stream subscription for transcription
#             await local_participant.set_subscribed(True)
#             logger.info("✅ Transcription stream handler configured")
#     except Exception as e:
#         logger.warning(f"⚠️ Could not set up transcription handler: {e}")

#     # 9. Send initial slide data to frontend
#     logger.info("📤 Sending initial slide to frontend...")
#     try:
#         await ctx.room.local_participant.set_attributes({
#             "total_slides": str(total_slides),
#             "current_slide_index": "0",
#             "presentation_status": "interactive",
#             "presentation_id": presentation_id
#         })
#         logger.info(f"✅ Sent metadata to frontend")
#     except Exception as e:
#         logger.error(f"❌ Failed to send metadata: {e}")

#     await asyncio.sleep(2.0)
    
#     # 10. Display first slide
#     try:
#         await update_slide_display()
#         logger.info("✅ First slide display updated.")
        
#         # Trigger the agent to start speaking
#         logger.info("🎙️ Triggering Dia to start presentation...")
        
#         # Create a small delay to ensure everything is ready
#         await asyncio.sleep(1.0)
        
#         # Send a welcome message through the room that the agent might pick up
#         try:
#             await ctx.room.local_participant.publish_data(
#                 b"Welcome to the presentation!",
#                 topic="presentation_start"
#             )
#         except:
#             pass  # Ignore if data publishing fails
            
#         logger.info("✅ Presentation ready. Dia should start speaking now.")
        
#     except Exception as e:
#         logger.error(f"❌ Error starting first slide presentation: {e}")
    
#     # 11. Enter interactive mode
#     logger.info("✅ Listening for voice commands...")
    
#     # Keep alive logic
#     await keep_alive(ctx)

#     # 12. Graceful shutdown handling
#     try:
#         # Monitor the session
#         while True:
#             await asyncio.sleep(5)
#             # Log status periodically
#             logger.debug("🔄 Agent session still active")
#     except asyncio.CancelledError:
#         logger.info("Agent session cancelled")
#     except Exception as e:
#         logger.error(f"Session error: {e}")
#     finally:
#         logger.info("Agent session ending")


# # ==================== NAVIGATION TOOL FUNCTIONS ====================

# @function_tool(description="Move to the next slide in the presentation. Use this when the user says 'next', 'next slide', or 'move forward'")
# async def next_slide():
#     """Move to the next slide in the presentation"""
#     global current_slide_index, total_slides, slides_data, room_context
    
#     if current_slide_index < total_slides - 1:
#         current_slide_index += 1
#         await update_slide_display()
        
#         slide = slides_data[current_slide_index]
#         content = slide.get("extracted_text", "")
        
#         logger.info(f"✅ Moved to slide {current_slide_index + 1}")
        
#         # Return detailed instructions for the agent to present this slide
#         return f"""I've moved to slide {current_slide_index + 1}. 

# SLIDE CONTENT:
# {content}

# PLEASE PRESENT THIS SLIDE BY:
# 1. Starting with: "Now let's look at slide {current_slide_index + 1}."
# 2. Presenting the key points in 2-3 sentences using professional Indian English.
# 3. Speaking clearly and at a moderate pace.
# 4. Ending with: "Shall we move to the next slide?"

# IMPORTANT: Speak naturally and engage with the content. Don't rush."""
#     else:
#         logger.info("Already on last slide")
#         return """This is the final slide. We've completed the presentation.

# PLEASE PROVIDE A CONCLUSION BY:
# 1. Saying: "This concludes our presentation."
# 2. Summarizing the key takeaways in 2-3 sentences.
# 3. Thanking the audience: "Thank you for your attention."
# 4. Ending with: "If you have any questions, I'd be happy to help."

# Speak clearly and professionally."""


# @function_tool(description="Move to the previous slide in the presentation. Use this when the user says 'previous', 'back', 'go back', or 'previous slide'")
# async def previous_slide():
#     """Move to the previous slide in the presentation"""
#     global current_slide_index, total_slides, slides_data
    
#     if current_slide_index > 0:
#         current_slide_index -= 1
#         await update_slide_display()
        
#         slide = slides_data[current_slide_index]
#         content = slide.get("extracted_text", "")
        
#         logger.info(f"✅ Moved to slide {current_slide_index + 1}")
        
#         return f"""I've moved back to slide {current_slide_index + 1}. 

# SLIDE CONTENT:
# {content}

# PLEASE REVISIT THIS SLIDE BY:
# 1. Starting with: "Let's revisit slide {current_slide_index + 1}."
# 2. Presenting the key points again in 2-3 sentences.
# 3. Speaking clearly and at a moderate pace.
# 4. Ending with: "Ready to continue?"

# IMPORTANT: Provide a brief recap of this slide's content."""
#     else:
#         logger.info("Already on first slide")
#         return "We're already on the first slide. I can present it again if you'd like."


# @function_tool(description="Jump to a specific slide number. Use this when the user says 'go to slide X' or 'show slide X' where X is a number")
# async def goto_slide(slide_number: int):
#     """Jump to a specific slide number in the presentation"""
#     global current_slide_index, total_slides, slides_data
    
#     if 1 <= slide_number <= total_slides:
#         current_slide_index = slide_number - 1
#         await update_slide_display()
        
#         slide = slides_data[current_slide_index]
#         content = slide.get("extracted_text", "")
        
#         logger.info(f"✅ Jumped to slide {slide_number}")
        
#         return f"""I've jumped to slide {slide_number}. 

# SLIDE CONTENT:
# {content}

# PLEASE PRESENT THIS SLIDE BY:
# 1. Starting with: "Let's look at slide {slide_number}."
# 2. Presenting the key points in 2-3 sentences using professional Indian English.
# 3. Speaking clearly and at a moderate pace.
# 4. Ending with: "Shall we continue?"

# IMPORTANT: Adapt your presentation style to this specific slide."""
#     else:
#         logger.warning(f"Invalid slide number: {slide_number}")
#         return f"Please choose a slide number between 1 and {total_slides}."


# async def update_slide_display():
#     """Update the frontend via room attributes to show the current slide"""
#     global current_slide_index, total_slides, room_context
    
#     if room_context is None:
#         logger.error("❌ Room context not available")
#         return
    
#     try:
#         await room_context.room.local_participant.set_attributes({
#             "current_slide_index": str(current_slide_index),
#             "total_slides": str(total_slides),
#             "presentation_status": "interactive"
#         })
#         logger.info(f"📊 Display updated: Slide {current_slide_index + 1}/{total_slides}")
#     except Exception as e:
#         logger.error(f"❌ Failed to update display: {e}")


# # ==================== HEALTH CHECK FUNCTION ====================

# async def check_session_health():
#     """Periodic health check for the agent session"""
#     global session, room_context
    
#     if session is None or room_context is None:
#         return False
    
#     try:
#         # Check if room is still connected
#         if not room_context.room.is_connected:
#             logger.warning("⚠️ Room is not connected")
#             return False
            
#         # Check if there are remote participants
#         if len(room_context.room.remote_participants) == 0:
#             logger.warning("⚠️ No remote participants")
#             return False
            
#         return True
#     except Exception as e:
#         logger.error(f"❌ Health check failed: {e}")
#         return False


# if __name__ == "__main__":
#     cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))





















import asyncio
import logging
import time
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

# Global state
current_slide_index = 0
slides_data = []
total_slides = 0
room_context = None
agent_instance = None
session = None
avatar = None
session_start_time = 0
presentation_id = None

# Session management
SESSION_TIMEOUT_SECONDS = 170  # 2 minutes 50 seconds (safety margin)
is_resetting_session = False

async def entrypoint(ctx: JobContext):
    global current_slide_index, slides_data, total_slides, room_context
    global agent_instance, session, avatar, session_start_time, presentation_id
    global is_resetting_session
    
    logger.info(f"🚀 Initializing agent for room: {ctx.room.name}")
    room_context = ctx
    session_start_time = time.time()

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

    # 4. Start the main presentation loop
    await start_presentation_session(ctx, presentation_id)

async def start_presentation_session(ctx, pid):
    """Start or restart a presentation session"""
    global current_slide_index, agent_instance, session, avatar, session_start_time
    global is_resetting_session
    
    if is_resetting_session:
        logger.info("⏳ Session reset in progress, waiting...")
        await asyncio.sleep(2)
    
    is_resetting_session = False
    session_start_time = time.time()
    
    # Initialize components
    llm_model = create_llm()
    avatar = create_avatar()
    
    # Create agent with current slide
    current_slide = slides_data[current_slide_index]
    slide_content = current_slide.get("extracted_text", "")
    
    agent_instructions = f"""{SYSTEM_INSTRUCTIONS}

CURRENT SLIDE ({current_slide_index + 1}/{total_slides}):

{slide_content}

PRESENTATION INSTRUCTIONS:
1. If this is the first slide (Slide 1), introduce yourself: "Hello, I'm Dia, your presentation assistant."
2. Present the key points in 2-3 sentences using professional Indian English.
3. Speak clearly and at a moderate pace.
4. End by asking: "Shall we move to the next slide?"
5. Keep responses concise and engaging.

NOTE: Session may restart due to technical limitations. If interrupted, simply continue from where we left off."""

    try:
        # Create agent
        agent_instance = Agent(
            instructions=agent_instructions,
            tools=[next_slide, previous_slide, goto_slide]
        )
        
        # Create session
        session = AgentSession(
            llm=llm_model,
            video_sampler=VoiceActivityVideoSampler(speaking_fps=0, silent_fps=0),
            preemptive_generation=False,
            min_endpointing_delay=1.5,
            max_endpointing_delay=3.0,
            resume_false_interruption=False,
        )
        
        # Attach avatar
        await avatar.start(session, room=ctx.room)
        
        # Start session
        await session.start(
            agent=agent_instance,
            room=ctx.room,
            room_input_options=room_io.RoomInputOptions(
                video_enabled=True,
                close_on_disconnect=False,
                audio_enabled=True,
            ),
        )
        
        logger.info(f"✅ Presentation session started (Slide {current_slide_index + 1})")
        
        # Update frontend
        await update_slide_display()
        
        # Start session monitor
        asyncio.create_task(monitor_session(ctx))
        
        # Keep alive
        await keep_alive(ctx)
        
    except Exception as e:
        logger.error(f"❌ Failed to start session: {e}")
        await handle_session_reset(ctx)

async def monitor_session(ctx):
    """Monitor session health and reset before timeout"""
    global session_start_time, is_resetting_session
    
    while True:
        await asyncio.sleep(10)  # Check every 10 seconds
        
        # Check if session needs reset (before 3-minute limit)
        elapsed = time.time() - session_start_time
        if elapsed >= SESSION_TIMEOUT_SECONDS and not is_resetting_session:
            logger.warning(f"⚠️ Session approaching limit ({elapsed:.0f}s). Preparing to reset...")
            await handle_session_reset(ctx)
            break
            
        # Check if session is still active
        if session and hasattr(session, 'is_running') and not session.is_running:
            logger.warning("⚠️ Session stopped unexpectedly")
            await handle_session_reset(ctx)
            break

async def handle_session_reset(ctx):
    """Handle session reset gracefully"""
    global session, avatar, is_resetting_session, current_slide_index
    
    if is_resetting_session:
        return  # Already resetting
    
    is_resetting_session = True
    logger.info("🔄 Resetting presentation session...")
    
    try:
        # Clean up current session
        if session:
            try:
                await session.aclose()
            except:
                pass
        
        if avatar:
            try:
                await avatar.stop()
            except:
                pass
        
        # Wait before restarting
        await asyncio.sleep(3)
        
        # Restart session
        await start_presentation_session(ctx, presentation_id)
        
    except Exception as e:
        logger.error(f"❌ Failed to reset session: {e}")

# ==================== NAVIGATION TOOLS ====================

@function_tool(description="Move to the next slide in the presentation")
async def next_slide():
    global current_slide_index, total_slides, slides_data, session_start_time
    
    if current_slide_index < total_slides - 1:
        current_slide_index += 1
        await update_slide_display()
        
        slide = slides_data[current_slide_index]
        content = slide.get("extracted_text", "")
        
        logger.info(f"✅ Moved to slide {current_slide_index + 1}")
        
        # Reset session timer on slide change
        session_start_time = time.time()
        
        return f"""Now presenting slide {current_slide_index + 1}.

SLIDE CONTENT:
{content}

Please present the key points in 2-3 sentences and ask if we should continue."""
    else:
        logger.info("Already on last slide")
        return "This is the final slide. Please provide a conclusion and thank the audience."

@function_tool(description="Move to the previous slide")
async def previous_slide():
    global current_slide_index, total_slides, slides_data, session_start_time
    
    if current_slide_index > 0:
        current_slide_index -= 1
        await update_slide_display()
        
        slide = slides_data[current_slide_index]
        content = slide.get("extracted_text", "")
        
        logger.info(f"✅ Moved to slide {current_slide_index + 1}")
        
        # Reset session timer
        session_start_time = time.time()
        
        return f"""Returning to slide {current_slide_index + 1}.

SLIDE CONTENT:
{content}

Please present this slide again."""
    else:
        return "We're already on the first slide."

@function_tool(description="Jump to a specific slide number")
async def goto_slide(slide_number: int):
    global current_slide_index, total_slides, slides_data, session_start_time
    
    if 1 <= slide_number <= total_slides:
        current_slide_index = slide_number - 1
        await update_slide_display()
        
        slide = slides_data[current_slide_index]
        content = slide.get("extracted_text", "")
        
        logger.info(f"✅ Jumped to slide {slide_number}")
        
        # Reset session timer
        session_start_time = time.time()
        
        return f"""Jumped to slide {slide_number}.

SLIDE CONTENT:
{content}

Please present this slide."""
    else:
        return f"Please choose a slide between 1 and {total_slides}."

async def update_slide_display():
    global current_slide_index, total_slides, room_context
    
    if room_context:
        try:
            await room_context.room.local_participant.set_attributes({
                "current_slide_index": str(current_slide_index),
                "total_slides": str(total_slides),
                "presentation_status": "interactive"
            })
            logger.info(f"📊 Display: Slide {current_slide_index + 1}/{total_slides}")
        except Exception as e:
            logger.error(f"❌ Failed to update display: {e}")

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))