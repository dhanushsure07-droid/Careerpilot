from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_reports_api_is_running() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
