# File: whisper.api/app/api/__init__.py
"""
API Router — Deepgram-style and OpenAI-compatible endpoint structure.

/v1/listen               → Speech-to-Text (Deepgram-compatible pre-recorded + WebSocket streaming)
/v1/audio/transcriptions → Speech-to-Text (OpenAI-compatible transcription)
/v1/audio/translations   → Speech-to-Text (OpenAI-compatible English translation)
/v1/models               → Available models
/v1/auth                 → API key management
"""

from fastapi import APIRouter
from .endpoints import audio, auth, listen, models

api_router = APIRouter()

api_router.include_router(listen.router, prefix="/listen", tags=["speech-to-text"])
api_router.include_router(audio.router, prefix="/audio", tags=["openai-audio"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
