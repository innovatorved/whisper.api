import uuid

from pydantic import BaseModel
from typing import Optional

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Integer, String, Boolean

from app.core.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship


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
