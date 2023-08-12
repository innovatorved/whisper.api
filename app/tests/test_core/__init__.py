from fastapi.testclient import TestClient
from app.core.config import settings


def test_app():
    from app.main import app
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_config():
    assert settings.app_name == "My FastAPI Project"
    assert settings.log_level == "debug"
    assert settings.max_connection_count == 10