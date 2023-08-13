from .AuthToken import AuthToken
from .User import UserInDB
from .Transcribe import TranscibeInDB

from app.core.database import Base, engine


Base.metadata.create_all(engine)
