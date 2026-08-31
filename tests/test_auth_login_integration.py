import app.db.base

from fastapi.testclient import TestClient

from app.main import app
from app.core.security import decode_access_token


USERS = [
    ("merchant1.demo@example.com", "MERCHANT"),
    ("merchant2.demo@example.com", "MERCHANT"),
    ("buyer1.demo@example.com", "BUYER"),
    ("buyer2.demo@example.com", "BUYER"),
]


def test_demo_users_auth_login_integration():
    client = TestClient(app)

    for email, expected_role in USERS:
        client.cookies.clear()

        login = client.post(
            "/auth/login",
            json={
                "email": email,
                "password": "Test1234!",
            },
        )

        assert login.status_code == 200, login.text

        data = login.json()
        token = data["access_token"]

        assert data["token_type"] == "bearer"
        assert token

        payload = decode_access_token(token)

        assert payload["sub"] == email
        assert payload["role"] == expected_role

        cookie = client.cookies.get("access_token")
        assert cookie is not None

        normalized_cookie = cookie.strip('"')
        assert normalized_cookie.startswith("Bearer ")

        me = client.get("/auth/me")

        assert me.status_code == 200, me.text
        assert me.json()["email"] == email
        assert me.json()["role"] == expected_role


if __name__ == "__main__":
    test_demo_users_auth_login_integration()
    print("===== PHASE 2M-D11 SAVED TEST PASS =====")
