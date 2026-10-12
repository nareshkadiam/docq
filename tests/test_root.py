from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_reports_service_and_version():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"service": "docq", "version": "v2"}
