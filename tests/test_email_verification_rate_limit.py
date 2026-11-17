from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.db.session import get_db
from app.routers import auth


@pytest.fixture(autouse=True)
def reset_email_verification_limiter():
    with auth._email_verification_rate_lock:
        auth._email_verification_attempts.clear()
        auth._email_verification_last_cleanup = 0.0

    yield

    with auth._email_verification_rate_lock:
        auth._email_verification_attempts.clear()
        auth._email_verification_last_cleanup = 0.0


def make_request(host):
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/auth/verify-email",
        "raw_path": b"/auth/verify-email",
        "query_string": b"",
        "headers": [],
        "client": (host, 12345),
        "server": ("testserver", 80),
    })


def test_allows_first_30_attempts_and_rejects_31st():
    request = make_request("192.0.2.10")

    for _ in range(30):
        allowed, retry_after = auth._check_email_verification_rate_limit(
            request
        )
        assert allowed is True
        assert retry_after == 0

    allowed, retry_after = auth._check_email_verification_rate_limit(
        request
    )

    assert allowed is False
    assert 1 <= retry_after <= 900


def test_rate_limit_is_independent_between_source_hosts():
    first = make_request("192.0.2.11")
    second = make_request("192.0.2.12")

    for _ in range(30):
        assert auth._check_email_verification_rate_limit(first)[0] is True

    assert auth._check_email_verification_rate_limit(first)[0] is False

    for _ in range(30):
        assert auth._check_email_verification_rate_limit(second)[0] is True


def test_attempts_expire_after_15_minutes(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(auth.time, "monotonic", lambda: clock[0])

    request = make_request("192.0.2.13")

    for _ in range(30):
        assert auth._check_email_verification_rate_limit(request)[0] is True

    assert auth._check_email_verification_rate_limit(request)[0] is False

    clock[0] += 901

    allowed, retry_after = auth._check_email_verification_rate_limit(
        request
    )

    assert allowed is True
    assert retry_after == 0


def test_malformed_code_is_rejected_without_counting_attempt():
    app = FastAPI()
    app.include_router(auth.router)
    app.dependency_overrides[get_db] = lambda: MagicMock()

    client = TestClient(app)

    response = client.post(
        "/auth/verify-email",
        data={"code": "12"},
    )

    assert response.status_code == 400
    assert auth._email_verification_attempts == {}


def test_rate_limited_response_contains_retry_after_header():
    app = FastAPI()
    app.include_router(auth.router)
    app.dependency_overrides[get_db] = lambda: MagicMock()

    request = make_request("testclient")
    for _ in range(30):
        assert auth._check_email_verification_rate_limit(request)[0] is True

    client = TestClient(app)
    response = client.post(
        "/auth/verify-email",
        data={"code": "123456"},
    )

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) >= 1


def test_valid_email_verification_succeeds_without_real_database(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    app = FastAPI()
    app.include_router(auth.router)

    user = SimpleNamespace(
        email_verification_token_hash=auth.hash_verification_token('123456'),
        email_verification_expires_at=(
            datetime.now(timezone.utc) + timedelta(hours=1)
        ),
        email_verified=False,
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    app.dependency_overrides[get_db] = lambda: db

    client = TestClient(app)
    response = client.post(
        "/auth/verify-email",
        data={"code": "123456"},
    )

    assert response.status_code == 200, response.text
    assert user.email_verified is True
    assert user.email_verification_token_hash is None
    assert user.email_verification_expires_at is None
    db.commit.assert_called_once()


def test_expired_email_verification_code_is_rejected(monkeypatch):
    from datetime import datetime, timedelta, timezone
    from types import SimpleNamespace

    app = FastAPI()
    app.include_router(auth.router)

    original_hash = "existing-verification-hash"
    expired_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    user = SimpleNamespace(
        email_verification_token_hash=original_hash,
        email_verification_expires_at=expired_at,
        email_verified=False,
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    app.dependency_overrides[get_db] = lambda: db

    client = TestClient(app)
    response = client.post(
        "/auth/verify-email",
        data={"code": "123456"},
    )

    assert response.status_code == 400
    assert user.email_verified is False
    assert user.email_verification_token_hash == original_hash
    assert user.email_verification_expires_at == expired_at
    db.commit.assert_not_called()

def test_full_source_table_evicts_least_recently_used_source(monkeypatch):
    from types import SimpleNamespace
    import app.routers.auth as auth

    monkeypatch.setattr(auth, "EMAIL_VERIFY_RATE_MAX_SOURCES", 2)
    monkeypatch.setattr(auth.time, "monotonic", lambda: 1000.0)

    auth._email_verification_attempts.clear()
    monkeypatch.setattr(auth, "_email_verification_last_cleanup", 0.0)

    def request_for(host):
        return SimpleNamespace(client=SimpleNamespace(host=host))

    allowed_a1 = auth._check_email_verification_rate_limit(
        request_for("192.0.2.20")
    )
    allowed_b = auth._check_email_verification_rate_limit(
        request_for("192.0.2.21")
    )
    allowed_a2 = auth._check_email_verification_rate_limit(
        request_for("192.0.2.20")
    )
    allowed_c = auth._check_email_verification_rate_limit(
        request_for("192.0.2.22")
    )

    assert allowed_a1 == (True, 0)
    assert allowed_b == (True, 0)
    assert allowed_a2 == (True, 0)
    assert allowed_c == (True, 0)

    assert list(auth._email_verification_attempts) == [
        "192.0.2.20",
        "192.0.2.22",
    ]
    assert len(auth._email_verification_attempts) == 2
    assert len(auth._email_verification_attempts["192.0.2.20"]) == 2
    assert "192.0.2.21" not in auth._email_verification_attempts
