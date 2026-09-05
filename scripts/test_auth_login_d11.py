from fastapi.testclient import TestClient

import app.db.base  # CENTRAL ORM REGISTRY — SINGLE SOURCE OF TRUTH
from app.main import app as fastapi_app
from app.core.security import decode_access_token

USERS = [
    ("merchant1.demo@example.com", "MERCHANT"),
    ("merchant2.demo@example.com", "MERCHANT"),
    ("buyer1.demo@example.com", "BUYER"),
    ("buyer2.demo@example.com", "BUYER"),
]

PASSWORD = "password123"



print("===== PHASE 2M-D11 — AUTH LOGIN INTEGRATION TEST =====")

client = TestClient(fastapi_app)

for email, expected_role in USERS:
    print(f"----- LOGIN: {email} -----")

    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    print("LOGIN STATUS:", response.status_code)
    print("LOGIN BODY:", response.text)

    assert response.status_code == 200, (
        f"LOGIN FAIL: {email} -> {response.status_code}: {response.text}"
    )

    body = response.json()
    token = body.get("access_token")

    assert token, f"JWT MISSING: {email}"
    print("JWT: PASS")

    payload = decode_access_token(token)

    assert payload.get("sub"), f"JWT SUBJECT MISSING: {email}"
    assert payload.get("role") == expected_role, (
        f"JWT ROLE FAIL: {email}: {payload.get('role')}"
    )
    print("JWT ROLE:", payload["role"], "PASS")

    cookie = client.cookies.get("access_token")
    assert cookie, f"ACCESS_TOKEN COOKIE MISSING: {email}"

    cookie_value = cookie.strip('"')
    assert cookie_value.startswith("Bearer "), (
        f"COOKIE FORMAT FAIL: {email}"
    )
    print("ACCESS_TOKEN COOKIE: PASS")

    me = client.get("/auth/me")

    print("ME STATUS:", me.status_code)
    print("ME BODY:", me.text)

    assert me.status_code == 200, (
        f"/auth/me FAIL: {email} -> {me.status_code}: {me.text}"
    )

    me_body = me.json()

    assert me_body.get("email") == email, (
        f"/auth/me EMAIL FAIL: {email}"
    )

    assert me_body.get("role") == expected_role, (
        f"/auth/me ROLE FAIL: {email}: {me_body.get('role')}"
    )

    print("/auth/me: PASS")
    print("ROLE PRESERVATION:", expected_role, "PASS")

    client.cookies.clear()

print("===== PHASE 2M-D11 PASS =====")
print("LOGIN: 4/4 PASS")
print("JWT: 4/4 PASS")
print("COOKIE: 4/4 PASS")
print("/auth/me: 4/4 PASS")
print("ROLE PRESERVATION: 4/4 PASS")
