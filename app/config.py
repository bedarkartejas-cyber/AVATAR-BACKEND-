import os
from dotenv import load_dotenv

# Load the environment variables from the .env file in your root directory
load_dotenv()

# --- LiveKit Settings ---
# These are used to generate the session token for the avatar
LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

# --- Supabase Settings ---
# Used to store the extracted slide text and image metadata
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# --- Storage Settings ---
# These must match the bucket names you created in your Supabase dashboard
BUCKET_PPTS = os.getenv("BUCKET_PPTS", "ppts")
BUCKET_IMAGES = os.getenv("BUCKET_IMAGES", "slide-images")

# --- PPT Processing (ConvertAPI) ---
# Used by the ppt_processor to turn slides into high-quality JPGs
CONVERTAPI_KEY = os.getenv("CONVERTAPI_KEY")

# --- AI Agent Settings ---
# Credentials for the Gemini LLM and Anam Avatar
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANAM_API_KEY = os.getenv("ANAM_API_KEY")
ANAM_AVATAR_ID = os.getenv("ANAM_AVATAR_ID")

# --- System Validation ---
# This helper print ensures your .env is actually being read
if not all([LIVEKIT_API_KEY, SUPABASE_URL, CONVERTAPI_KEY]):
    print("⚠️ WARNING: Essential environment variables are missing in your .env file!")
else:
    print("✅ Configuration loaded successfully.")