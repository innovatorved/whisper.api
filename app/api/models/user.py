from pydantic import BaseModel
from typing import Optional

from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base


class UserBase(BaseModel):
    email: str
    username: str


class UserResponse(UserBase):
    is_active: Optional[bool]

    class Config:
        from_attributes = True


class User(UserBase):
    is_active: Optional[bool]
    password: str

    class Config:
        from_attributes = True


class UpdateUser(UserBase):
    current_password: str


class UserInDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

    def __init__(self, username: str, email: str, hashed_password: str):
        self.username = username
        self.email = email
        self.hashed_password = hashed_password
