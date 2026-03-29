"""
Models Endpoint — List available Whisper models.

GET /v1/models  → List all available models with metadata
"""

from fastapi import APIRouter

from app.utils.utils import list_available_models

router = APIRouter()


@router.get(
    "",
    summary="List Available Models",
    description="List all available Whisper models with metadata.",
    tags=["models"],
)
async def get_models():
    """
    Returns a list of available models that can be used with the listen endpoint.

    Each model includes:
    - `model_id`: Use this value for the `model` query parameter
    - `name`: Human-readable model name
    - `description`: Model description
    - `language`: Supported language
    - `version`: Model version
    - `size_bytes`: Model file size
    """
    models = list_available_models()
    return {
        "models": models,
        "count": len(models),
    }
