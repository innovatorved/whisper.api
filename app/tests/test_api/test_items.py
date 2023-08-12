from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_item():
    data = {"name": "test", "description": "test description"}
    response = client.post("/items/", json=data)
    assert response.status_code == 200
    assert response.json()["name"] == "test"
    assert response.json()["description"] == "test description"


def test_read_item():
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json()["name"] == "test"
    assert response.json()["description"] == "test description"


def test_read_all_items():
    response = client.get("/items/")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_update_item():
    data = {"name": "updated test", "description": "updated test description"}
    response = client.put("/items/1", json=data)
    assert response.status_code == 200
    assert response.json()["name"] == "updated test"
    assert response.json()["description"] == "updated test description"


def test_delete_item():
    response = client.delete("/items/1")
    assert response.status_code == 200
    assert response.json() == {"detail": "Item deleted successfully"}
