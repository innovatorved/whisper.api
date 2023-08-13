import uuid

from pydantic import BaseModel
from typing import Optional

from sqlalchemy.dialects.postgresql import UUID

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
