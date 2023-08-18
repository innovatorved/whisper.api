import uuid
import re
from datetime import datetime


from pydantic import ConfigDict, BaseModel, Field, field_validator
from typing import Optional

from sqlalchemy import Column, Integer, String, Boolean

from app.core.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship


class UserBase(BaseModel):
    email: str
    username: str


class UserResponse(UserBase):
    id: uuid.UUID = Field(..., alias="id")
    is_active: Optional[bool] = None
    created_at: datetime = Field(..., alias="created_at")
    model_config = ConfigDict(
        from_attributes=True,
    )


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class User(UserBase):
    password: str

    @field_validator("email")
    def email_must_be_valid(cls, v):
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise ValueError("Invalid email address")
        return v

    @field_validator("password")
    def password_must_be_long(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long")
        return v

    model_config = ConfigDict(from_attributes=True)


class UpdateUser(UserBase):
    current_password: str


class UserDeletedResponse(BaseModel):
    detail: str = Field(..., alias="detail")
    model_config = ConfigDict(from_attributes=True)
