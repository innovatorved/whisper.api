import uuid

from fastapi.testclient import TestClient
from app.main import app

from app.tests.utils.utils import fake_user_details, get_new_fake_pwd

client = TestClient(app)

test_user_details = fake_user_details()


def test_create_user():
    data = {
        "email": test_user_details["email"],
        "username": test_user_details["username"],
        "password": test_user_details["password"],
    }
    response = client.post("/api/v1/users/", json=data)
    print(response.content)
    test_user_details["user_id"] = response.json()["id"]
    assert response.status_code == 201
    assert response.json()["email"] == test_user_details["email"]
    assert response.json()["username"] == test_user_details["username"]


def test_create_user_invalid_email():
    test_user_details_2 = fake_user_details()

    data = {
        "email": "invalid_email",
        "username": test_user_details_2["username"],
        "password": test_user_details_2["password"],
    }
    response = client.post(f"/api/v1/users/", json=data)
    assert response.status_code == 422
    assert "value_error" in response.json()["detail"][0]["type"]
    assert "Invalid email" in response.json()["detail"][0]["msg"]


def test_create_user_invalid_password():
    data = {
        "email": test_user_details["email"],
        "username": test_user_details["username"],
        "password": "short",
    }
    response = client.post("/api/v1/users/", json=data)
    assert response.status_code == 422
    assert (
        "Password must be at least 6 characters long"
        in response.json()["detail"][0]["msg"]
    )


def test_read_user():
    response = client.get(f"/api/v1/users/{test_user_details['user_id']}")
    assert response.status_code == 200
    assert response.json()["email"] == test_user_details["email"]
    assert response.json()["username"] == test_user_details["username"]


def test_read_user_not_found():
    response = client.get(f"/api/v1/users/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_check_update_password():
    new_password = get_new_fake_pwd()
    data = {
        "current_password": test_user_details["password"],
        "new_password": new_password,
    }
    response = client.put(
        f"/api/v1/users/{test_user_details['user_id']}/update_password/", json=data
    )
    assert response.status_code == 200
    assert response.json()["email"] == test_user_details["email"]
    assert response.json()["username"] == test_user_details["username"]


def test_check_update_password_invalid_current_password():
    new_password = get_new_fake_pwd()
    data = {"current_password": "wrong_password", "new_password": new_password}
    response = client.put(
        f"/api/v1/users/{test_user_details['user_id']}/update_password/", json=data
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect password"


def test_check_update_password_not_found():
    data = {"current_password": "wrong_password", "new_password": "new_password"}
    response = client.put(f"/api/v1/users/{uuid.uuid4()}/update_password/", json=data)
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_delete_user_not_found():
    response = client.delete(f"/api/v1/users/{uuid.uuid4()}/delete")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"
