from sqlalchemy.orm import Session
from app.core.database import SessionLocal

from faker import Faker

fake = Faker()


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


def fake_user_details():
    test_user_details = {
        "email": fake.email(),
        "username": fake.user_name(),
        "password": fake.password(),
    }
    return test_user_details


def get_new_fake_pwd():
    return fake.password()
