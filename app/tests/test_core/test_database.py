from sqlalchemy.orm import Session
from app.core.database import Base
from app.api.models.user import User
from app.api.models.item import Item


def test_create_user(db: Session):
    user = User(email="test@example.com", password="password123")
    db.add(user)
    db.commit()
    db.refresh(user)
    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.is_active is True


def test_create_item(db: Session):
    item = Item(name="test item", description="test description")
    db.add(item)
    db.commit()
    db.refresh(item)
    assert item.id is not None
    assert item.name == "test item"
    assert item.description == "test description"
