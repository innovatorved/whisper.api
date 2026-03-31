# File: whisper.api/app/api/__init__.py
"""
API Router — Deepgram-style endpoint structure.

/v1/listen   → Speech-to-Text (pre-recorded + streaming)
/v1/models   → Available models
/v1/auth     → API key management
"""

from fastapi import APIRouter
from .endpoints import listen, models, auth

api_router = APIRouter()

api_router.include_router(listen.router, prefix="/listen", tags=["speech-to-text"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
