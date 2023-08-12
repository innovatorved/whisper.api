from fastapi.testclient import TestClient
from app.core.config import settings

client = TestClient(settings.app)


def test_create_user():
    data = {"email": "test@example.com", "password": "password"}
    response = client.post("/users/", json=data)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_create_user_invalid_email():
    data = {"email": "invalid_email", "password": "password"}
    response = client.post("/users/", json=data)
    assert response.status_code == 422
    assert "value_error.email" in response.json()["detail"][0]["type"]


def test_create_user_invalid_password():
    data = {"email": "test@example.com", "password": "short"}
    response = client.post("/users/", json=data)
    assert response.status_code == 422
    assert "ensure this value has at least 6 characters" in response.json()["detail"][0]["msg"]


def test_read_user():
    response = client.get("/users/1")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_read_user_not_found():
    response = client.get("/users/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_update_user():
    data = {"email": "new_email@example.com", "password": "new_password"}
    response = client.put("/users/1", json=data)
    assert response.status_code == 200
    assert response.json()["email"] == "new_email@example.com"


def test_update_user_not_found():
    data = {"email": "new_email@example.com", "password": "new_password"}
    response = client.put("/users/999", json=data)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_delete_user():
    response = client.delete("/users/1")
    assert response.status_code == 200
    assert response.json() == {"msg": "User deleted"}


def test_delete_user_not_found():
    response = client.delete("/users/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"