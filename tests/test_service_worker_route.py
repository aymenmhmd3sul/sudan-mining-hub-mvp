from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_service_worker_route_returns_javascript_with_root_scope():
    project_root = Path(__file__).resolve().parents[1]
    service_worker_file = project_root / "app" / "static" / "service-worker.js"
    assert service_worker_file.is_file()

    expected_content = service_worker_file.read_bytes()

    with TestClient(app) as client:
        response = client.get("/service-worker.js")

    assert response.status_code == 200
    assert "javascript" in response.headers.get("content-type", "").lower()
    assert response.headers.get("service-worker-allowed") == "/"
    assert response.content == expected_content
