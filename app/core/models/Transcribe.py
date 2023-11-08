from datetime import datetime, timedelta

import uuid
from app.core.config import settings

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base, engine


class TranscibeInDB(Base):
    __tablename__ = "transcribe_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text = Column(String)
    audio_duration = Column(Integer)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    user = relationship("UserInDB", back_populates="transcribes")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, user_id, text, audio_duration):
        self.text = text
        self.audio_duration = audio_duration
        self.user_id = user_id


class TranscribeController:
    TranscibeInDB = TranscibeInDB

    def __init__(self, database):
        self.db = database

    def create(self, user_id: UUID, text: str, duration: int):
        try:
            self.user_id = user_id
            self.text = text
            self.audio_duration = duration
            self.transcribe_data = TranscibeInDB(
                user_id=self.user_id, text=self.text, audio_duration=self.audio_duration
            )
            self.db.add(self.transcribe_data)
            self.db.commit()
            self.db.refresh(self.transcribe_data)
        except Exception as e:
            self.db.rollback()
            raise e
