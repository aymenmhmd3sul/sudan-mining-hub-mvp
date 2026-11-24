from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.routers import ui
from app.routers.auth import get_current_user


@pytest.fixture
def http_client():
    db = MagicMock()
    user = SimpleNamespace(
        id=101,
        role=SimpleNamespace(value="BUYER"),
        is_approved=True,
    )

    original_overrides = dict(app.dependency_overrides)

    def fake_db():
        yield db

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[ui.require_active_subscription] = lambda: user

    try:
        with TestClient(app) as client:
            yield client, db
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


def test_legacy_query_string_message_is_rejected(http_client):
    client, db = http_client

    response = client.post(
        "/api/v1/negotiation/701/messages",
        params={"body": "sensitive message"},
    )

    assert response.status_code == 422
    db.query.assert_not_called()


def test_empty_json_message_is_rejected(http_client):
    client, db = http_client

    response = client.post(
        "/api/v1/negotiation/701/messages",
        json={"body": ""},
    )

    assert response.status_code == 422
    db.query.assert_not_called()


def test_message_over_2000_characters_is_rejected(http_client):
    client, db = http_client

    response = client.post(
        "/api/v1/negotiation/701/messages",
        json={"body": "x" * 2001},
    )

    assert response.status_code == 422
    db.query.assert_not_called()


def test_message_with_exactly_2000_characters_is_accepted(
    http_client, monkeypatch
):
    client, db = http_client

    monkeypatch.setattr(
        ui.NegotiationService,
        "get_room",
        MagicMock(return_value=None),
    )

    response = client.post(
        "/api/v1/negotiation/701/messages",
        json={"body": "x" * 2000},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Negotiation room not found"
    db.query.assert_not_called()


def test_valid_json_message_reaches_negotiation_route(
    http_client, monkeypatch
):
    client, db = http_client

    monkeypatch.setattr(
        ui.NegotiationService,
        "get_room",
        MagicMock(return_value=None),
    )

    response = client.post(
        "/api/v1/negotiation/701/messages",
        json={"body": "Valid JSON message"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Negotiation room not found"
    db.query.assert_not_called()
