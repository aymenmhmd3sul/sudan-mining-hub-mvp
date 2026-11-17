from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.models.user import UserRole
from app.routers import deals
from app.routers.auth import get_current_user, require_active_subscription


app = FastAPI()
app.include_router(deals.router)


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def make_user(role):
    return SimpleNamespace(
        id=137,
        role=role,
        is_approved=(role == UserRole.MERCHANT),
    )


def make_client(user):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = (
        SimpleNamespace(id=51)
    )

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_active_subscription] = lambda: user

    return TestClient(app), db


@pytest.mark.parametrize("role", [UserRole.BUYER, UserRole.MERCHANT])
@pytest.mark.parametrize(
    "action,service_method",
    [
        ("approve", "approve_by_buyer"),
        ("receive", "mark_received"),
    ],
)
def test_buyer_and_merchant_can_use_buyer_deal_actions(
    role, action, service_method, monkeypatch
):
    user = make_user(role)
    client, db = make_client(user)

    service = MagicMock(return_value={"deal_id": 51, "result": "ok"})
    monkeypatch.setattr(deals.DealService, service_method, service)

    with client:
        response = client.post(f"/deals/51/{action}")

    assert response.status_code == 200, response.text
    assert response.json()["deal_id"] == 51

    service.assert_called_once_with(db, db.query.return_value.filter.return_value.first(), user.id)


@pytest.mark.parametrize("role", [UserRole.AGENT, UserRole.ADMIN])
@pytest.mark.parametrize("action", ["approve", "receive"])
def test_agent_and_admin_cannot_use_buyer_deal_actions(role, action):
    user = make_user(role)
    client, db = make_client(user)

    with client:
        response = client.post(f"/deals/51/{action}")

    assert response.status_code == 403, response.text
    db.commit.assert_not_called()
