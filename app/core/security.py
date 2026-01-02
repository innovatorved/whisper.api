from passlib.context import CryptContext
from fastapi import HTTPException

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
SECRET_KEY = settings.SECRET_KEY


def get_password_hash(password: str) -> str:
    """
    Hashes a password using bcrypt algorithm.
    Truncates to 72 bytes for bcrypt compatibility.
    """
    return pwd_context.hash(password[:72])


def verify_password(password: str, hash: str) -> bool:
    """
    Verifies a password against a bcrypt hash.
    Truncates to 72 bytes for bcrypt compatibility.
    """
    is_valid = pwd_context.verify(password[:72], hash)
    if not is_valid:
        return False
    return True
