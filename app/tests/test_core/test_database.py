from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.models.User import UserController

from app.tests.utils.utils import fake_user_details


def test_create_user(db: Session = SessionLocal()):
    test_user_details = fake_user_details()
    USER = UserController(db)
    USER.create(
        test_user_details["username"],
        test_user_details["email"],
        test_user_details["password"],
    )
    data = USER.details()
    assert data.id is not None
    assert data.email == test_user_details["email"]
    assert data.is_active is True
