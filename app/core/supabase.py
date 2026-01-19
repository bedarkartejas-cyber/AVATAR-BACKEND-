import os
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables from the .env file for local development
load_dotenv()

# Initialize the Supabase Client
# SUPABASE_URL: The unique endpoint for your project.
# SUPABASE_SERVICE_KEY: The secret key that allows the backend to bypass Row Level Security.
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)