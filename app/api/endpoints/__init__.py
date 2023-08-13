# File: whisper.api/app/api/endpoints/__init__.py

from fastapi import APIRouter

from . import items, users, transcribe

router = APIRouter()

router.include_router(items.router, prefix="/items", tags=["items"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(transcribe.router, prefix="/transcribe", tags=["transcribe"])
