# app/llm/gemini.py
from livekit.plugins import google
from app.config import GEMINI_API_KEY
from app.avatar.persona import SYSTEM_INSTRUCTIONS

def create_llm():
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is missing. Check your .env file.")
        
    return google.realtime.RealtimeModel(
        model="gemini-2.5-flash-native-audio-preview-09-2025", 
        api_key=GEMINI_API_KEY,  # This line is critical
        voice="Aoede",
        instructions=SYSTEM_INSTRUCTIONS,
        temperature=0.6,
    )