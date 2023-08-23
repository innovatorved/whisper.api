from app.core.database import Base, engine

from .AuthToken import AuthToken, AuthTokenController
from .Transcribe import TranscibeInDB, TranscribeController
from .User import UserInDB

Base.metadata.create_all(engine)
