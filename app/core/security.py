from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SECRET_KEY = settings.SECRET_KEY


def get_password_hash(password: str) -> str:
    """
    Hashes a password using bcrypt algorithm
    """
    return pwd_context.hash(password)


def verify_password(password: str, hash: str) -> bool:
    """
    Verifies a password against a bcrypt hash
    """
    return pwd_context.verify(password, hash)
