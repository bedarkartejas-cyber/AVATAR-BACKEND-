from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from livekit import api
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# 🔥 DEV MODE: allow ALL origins (no CORS headaches)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/token")
def token():
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    url = os.getenv("LIVEKIT_URL")

    if not api_key or not api_secret:
        return {"error": "LIVEKIT_API_KEY or LIVEKIT_API_SECRET missing"}

    at = (
        api.AccessToken(api_key, api_secret)
        .with_identity("user-1")
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room="demo-room"
            )
        )
    )

    return {
        "token": at.to_jwt(),
        "url": url
    }
