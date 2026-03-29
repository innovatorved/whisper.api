import uuid
import random
import string

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def generate_bearer_token() -> str:
    token_prefix = str(uuid.uuid4()).replace("-", "")
    token_suffix = "".join(
        random.choices(
            string.ascii_uppercase + string.ascii_lowercase + string.digits, k=32
        )
    )
    return f"{token_prefix}{token_suffix}"

