import uuid
import random
import string

from app.core.config import settings

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from sqlalchemy.sql import func

from app.core.database import Base


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("UserInDB", back_populates="auth_tokens")

    def __init__(self, user_id: UUID, token: str):
        self.user_id = user_id
        self.token = token


class AuthTokenController:
    AuthToken = AuthToken

    def __init__(self, database):
        self.db = database

    def get_userid_from_token(self, token) -> str:
        user = self.db.query(AuthToken).filter(AuthToken.token == token).first()
        if not user:
            raise Exception("Invalid Token!")
        return user.user_id

    def get_token_from_user_id(self, user_id: UUID) -> str:
        token = self.db.query(AuthToken).filter(AuthToken.user_id == user_id).first()
        if not token:
            raise Exception("Invalid Token!")
        self.auth_token = token

    def create(self, user_id: UUID):
        self.user_id = user_id
        self.token = self.create_token()
        self.auth_token = AuthToken(self.user_id, self.token)
        self.db.add(self.auth_token)
        self.db.commit()
        self.db.refresh(self.auth_token)

    def get_token(self):
        return self.auth_token.token

    def create_token(self):
        token = self.generate_bearer_token()
        return token

    def generate_bearer_token(self):
        token_prefix = str(uuid.uuid4()).replace("-", "")
        token_suffix = "".join(
            random.choices(
                string.ascii_uppercase + string.ascii_lowercase + string.digits, k=32
            )
        )
        return f"{token_prefix}{token_suffix}"

    @staticmethod
    def validate_bearer_token(request_token: str):
        ...
