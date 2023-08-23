import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import Base, SessionLocal


@pytest.fixture(scope="module")
def test_app():
    # set up test app with client
    from app.main import app

    client = TestClient(app)
    # set up test database
    TEST_DATABASE_URL = settings.TEST_DATABASE_URL
    engine = create_engine(TEST_DATABASE_URL)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    # yield the app and database session to the test
    try:
        yield client, TestingSessionLocal()
    finally:
        # clean up test database
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    # set up a new database session for each test
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
