import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router  # We will update routes.py next
from app.config import LIVEKIT_URL  # Verifies config.py is working

# Initialize the FastAPI application
app = FastAPI(
    title="Unified Dia AI Presenter",
    description="Backend for PPT Processing and LiveKit Avatar Integration",
    version="2.0.0"
)

# --- CRITICAL: Unified CORS Configuration ---
# This is the most important part for fixing your popup error.
# It tells the browser that your index.html (port 5500) is allowed
# to send data to this server (port 8000).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (ideal for local development)
    allow_credentials=True,
    allow_methods=["*"],  # Allows POST, GET, OPTIONS, etc.
    allow_headers=["*"],  # Allows Content-Type and Authorization headers
)

# 1. Include the consolidated routes
# This brings in the /upload-ppt and /livekit/token endpoints
app.include_router(router)

# 2. System Health Check
# You can visit http://localhost:8000/ in your browser to check if the API is alive.
@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "Unified AI Presenter",
        "livekit_url": LIVEKIT_URL
    }

# 3. Production-Ready Entrypoint
# This starts the server using Uvicorn when you run 'python -m app.api.main'
if __name__ == "__main__":
    # We use port 8000 as the single unified port
    port = int(os.getenv("PORT", 8000))
    
    print(f"🚀 Starting Unified Server on port {port}")
    print(f"📡 API Documentation available at: http://localhost:{port}/docs")
    
    uvicorn.run(
        "app.api.main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=True  # Automatically restarts the server when you save code changes
    )