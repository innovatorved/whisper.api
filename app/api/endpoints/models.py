"""
Models Endpoint — List available Whisper models.

GET /v1/models  → List all available models with metadata
"""

from fastapi import APIRouter, Query

from app.utils.utils import list_available_models

router = APIRouter()


@router.get(
    "",
    summary="List Available Models",
    description="List all available Whisper models with metadata.",
    tags=["models"],
)
async def get_models(
    include_uninstalled: bool = Query(
        False,
        description="Include registered models that have not yet been downloaded locally.",
    ),
):
    """
    Returns a list of available models that can be used with the listen or audio endpoints.
    """
    models = list_available_models(include_uninstalled=include_uninstalled)
    return {
        "models": models,
        "count": len(models),
    }
