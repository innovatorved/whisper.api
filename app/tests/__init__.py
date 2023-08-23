import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.main import app
from app.tests.utils.utils import get_db, override_get_db

# Create test database
TEST_DATABASE_URL = settings.TEST_DATABASE_URL
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Define test client
@pytest.fixture(scope="module")
def test_client():
    with TestClient(app) as client:
        yield client


# Define test database
@pytest.fixture(scope="module")
def test_db():
    db = TestingSessionLocal()
    yield db
    db.close()


# Override get_db function for testing
@pytest.fixture(autouse=True)
def override_get_db(monkeypatch):
    monkeypatch.setattr("app.api.dependencies.get_db", get_db)
