from datetime import datetime, timedelta
import uuid
import random
import string

from app.core.config import settings

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func

from app.core.database import Base, engine


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, user_id: UUID):
        self.user_id = user_id
        self.token = self.create_token()

    def create_token(self):
        token = self.generate_bearer_token()
        return token

    def generate_bearer_token(self):
        token_prefix = str(self.id).replace("-", "")  # Remove hyphens from UUID
        token_suffix = str(uuid.uuid4().hex)  # Generate a random UUID string
        return f"{token_prefix}{token_suffix}"

    @staticmethod
    def validate_bearer_token(request_token):
        ...
