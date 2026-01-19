import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.config import LIVEKIT_URL

# 1. Initialize FastAPI with production metadata
app = FastAPI(
    title="Unified Dia AI Presenter API",
    description="Backend for PPT processing and LiveKit Avatar integration.",
    version="2.0.0"
)

# 2. Configure CORS (Cross-Origin Resource Sharing)
# Using "*" allows all origins (localhost:3000, 5500, etc.) to communicate with the API.
# Critical for resolving preflight OPTIONS 400 errors during cross-port requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Global permission for all origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"], # Mandatory for browser preflight
    allow_headers=["*"],
)

# 3. Include Slide & Token Routes
app.include_router(router)

# 4. System Health Check (Root)
@app.get("/", tags=["System"])
async def root():
    """
    Standard health check for cloud load balancers.
    """
    return {
        "status": "online",
        "service": "Unified AI Presenter",
        "livekit_url": LIVEKIT_URL,
        "environment": os.getenv("ENVIRONMENT", "development")
    }

# 5. Dedicated Health Check
# Added to satisfy Render/Cloud health monitors explicitly looking for /health
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "service": "api-routes-dia"}

# 6. Production Server Entrypoint
if __name__ == "__main__":
    # Use the port assigned by Render or default to 8000
    port = int(os.getenv("PORT", 8000))
    
    # Toggle reload based on the ENVIRONMENT variable
    is_dev = os.getenv("ENVIRONMENT", "development") == "development"
    
    print(f"🚀 Starting Unified Server on port {port} (Dev Mode: {is_dev})")
    print(f"📡 Serving Global CORS (Allow Origins: *)")
    
    uvicorn.run(
        "app.api.main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=is_dev,
        workers=int(os.getenv("WEB_CONCURRENCY", 1))
    )
