from .ApiKey import ApiKey

from app.core.database import Base, engine


Base.metadata.create_all(engine)
