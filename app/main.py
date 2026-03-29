"""
Whisper Speech-to-Text API

A self-hosted speech-to-text API powered by whisper.cpp.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.api import api_router
from app.core.config import settings
from app.core.errors import error_handler
from app.utils import print_routes
from app.utils.checks import run_checks

if not run_checks():
    raise Exception("Failed to pass all checks")


app = FastAPI(
    title="Whisper Speech-to-Text API",
    description=(
        "A self-hosted speech-to-text API powered by whisper.cpp. "
        "Supports pre-recorded audio transcription and live streaming via WebSocket."
    ),
    version="2.0.0",
    openapi_url="/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse(url="/docs")


@app.get("/ping", tags=["health"])
async def ping():
    """Health check endpoint."""
    return {"ping": "pong", "status": "healthy"}


# Include routers under /v1
app.include_router(api_router, prefix="/v1")

# Error handlers
app.add_exception_handler(500, error_handler)

# Print all routes
print_routes(app)
