# File: my-fastapi-project/app/tests/test_api/__init__.py

from fastapi.testclient import TestClient
from my_fastapi_project.app.api import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"msg": "Hello World"}