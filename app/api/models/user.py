import uuid
from datetime import datetime


from pydantic import BaseModel, Field
from typing import Optional

from sqlalchemy import Column, Integer, String, Boolean

from app.core.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship


class UserBase(BaseModel):
    email: str
    username: str


class UserResponse(UserBase):
    id: uuid.UUID = Field(..., alias="id")
    is_active: Optional[bool]
    created_at: datetime = Field(..., alias="created_at")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            uuid.UUID: lambda u: str(u),
        }


class User(UserBase):
    password: str

    class Config:
        from_attributes = True


class UpdateUser(UserBase):
    current_password: str
