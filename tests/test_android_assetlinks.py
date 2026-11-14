from fastapi.testclient import TestClient

from app.main import app


def test_android_assetlinks_matches_release_identity():
    response = TestClient(app).get("/.well-known/assetlinks.json")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    data = response.json()

    assert len(data) == 1
    assert data[0]["relation"] == [
        "delegate_permission/common.handle_all_urls"
    ]
    assert data[0]["target"]["namespace"] == "android_app"
    assert data[0]["target"]["package_name"] == "app.sudanmininghub"
    assert data[0]["target"]["sha256_cert_fingerprints"] == [
        "41:44:5C:FA:1A:6D:56:AD:B4:95:DB:6D:BE:B3:18:3D:C0:EE:4E:EC:A4:21:E0:2D:76:35:D0:81:45:B1:D4:D9"
    ]
