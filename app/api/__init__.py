# File: whisper.api/app/api/__init__.py

from fastapi import APIRouter
from .endpoints import items, users

api_router = APIRouter()

api_router.include_router(items.router, prefix="/items", tags=["items"])
api_router.include_router(users.router, prefix="/users", tags=["users"])