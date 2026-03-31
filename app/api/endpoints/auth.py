from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.models.ApiKey import ApiKey, generate_bearer_token

router = APIRouter()

@router.post("/test-token", summary="Generate a test token (if enabled)")
def generate_test_token(name: str = "test-token", db: Session = Depends(get_db)):
    """
    Generate an API token for testing purposes.
    This endpoint is only available if ENABLE_TEST_TOKEN_ENDPOINT=true in the environment/config.
    """
    if not settings.ENABLE_TEST_TOKEN_ENDPOINT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test token generation is disabled. Set ENABLE_TEST_TOKEN_ENDPOINT=true to enable."
        )

    token_string = generate_bearer_token()
    new_key = ApiKey(token=token_string, name=name)
    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    return {
        "success": True,
        "token": token_string,
        "name": new_key.name,
        "message": "Keep this token safe! Pass it in the Authorization header as: Token <token> or via the ?token= query parameter."
    }
