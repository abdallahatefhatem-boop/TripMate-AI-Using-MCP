from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_home_page_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "TripMate" in response.text
    assert "html" in response.headers.get("content-type", "")


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "TripMate-AI"}
