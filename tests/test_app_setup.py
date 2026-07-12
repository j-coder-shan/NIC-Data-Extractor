from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_root_endpoint() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "NIC Data Extractor API"


def test_extract_route_exists() -> None:
    response = client.post("/api/extract")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "pending"
