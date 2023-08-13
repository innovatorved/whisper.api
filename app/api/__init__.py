# File: whisper.api/app/api/__init__.py

from fastapi import APIRouter
from .endpoints import items, users, transcribe

api_router = APIRouter()

api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(transcribe.router, prefix="/transcribe", tags=["transcribe"])
