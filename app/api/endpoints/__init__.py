# File: whisper.api/app/api/endpoints/__init__.py

from fastapi import APIRouter

from . import transcribe, users

router = APIRouter()

router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(transcribe.router, prefix="/transcribe", tags=["transcribe"])
