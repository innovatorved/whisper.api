from .AuthToken import AuthToken, AuthTokenController
from .User import UserInDB
from .Transcribe import TranscibeInDB, TranscribeController

from app.core.database import Base, engine


Base.metadata.create_all(engine)
