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
# This allows your frontend (index.html) to talk to this backend server.
raw_origins = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:8000")
origins = [origin.strip() for origin in raw_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# 3. Include Slide & Token Routes
app.include_router(router)

# 4. System Health Check
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

# 5. Production Server Entrypoint
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    # Enable auto-reload only in development mode
    is_dev = os.getenv("ENVIRONMENT", "development") == "development"
    
    print(f"🚀 Starting Unified Server on port {port} (Dev Mode: {is_dev})")
    
    uvicorn.run(
        "app.api.main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=is_dev,
        workers=int(os.getenv("WEB_CONCURRENCY", 1))
    )
