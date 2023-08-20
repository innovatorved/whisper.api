from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

POSTGRES_DATABASE_URL = settings.POSTGRES_DATABASE_URL

meta = MetaData()

engine = create_engine(POSTGRES_DATABASE_URL)
Base = declarative_base(metadata=meta)

Base.metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
