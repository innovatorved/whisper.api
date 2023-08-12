from sqlalchemy.orm import Session
from app.core.database import SessionLocal


def override_get_db():
    """
    Override the get_db function for testing
    """
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_db():
    """
    Get a new database session
    """
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()
