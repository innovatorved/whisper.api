import uuid


from app.core.config import settings

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base

from app.core.security import get_password_hash, verify_password


class UserInDB(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    transcribes = relationship("TranscibeInDB", back_populates="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, username: str, email: str, hashed_password: str):
        self.username = username
        self.email = email
        self.hashed_password = hashed_password

    def data(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at,
        }


class UserController:
    UserInDB = UserInDB

    def __init__(self, database):
        self.db = database

    def create(self, username: str, email: str, password: str):
        self.username = username
        self.email = email
        self.hashed_password = get_password_hash(password)
        db_user = UserInDB(
            username=self.username,
            email=self.email,
            hashed_password=self.hashed_password,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        self.user = db_user.data()

    def details(self):
        return self.user
