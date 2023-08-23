# File: whisper.api/app/tests/test_api/__init__.py

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_ping_main():
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong"}
