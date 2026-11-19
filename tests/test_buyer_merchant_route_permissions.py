from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.models.user import UserRole
from app.routers.auth import get_current_user, require_active_subscription
from app.routers import offers, requests, ui


app = FastAPI()
app.include_router(ui.router)
app.include_router(offers.router)
app.include_router(requests.router)


@pytest.fixture(autouse=True)
def clear_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def make_client(user):
    db = MagicMock()

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[require_active_subscription] = lambda: user

    return TestClient(app), db


def make_user(role):
    return SimpleNamespace(
        id=137,
        role=role,
        is_approved=(role == UserRole.MERCHANT),
    )


@pytest.mark.parametrize("role", [UserRole.BUYER, UserRole.MERCHANT])
def test_buyer_and_merchant_can_list_own_requests(role, monkeypatch):
    user = make_user(role)
    client, db = make_client(user)

    request_item = SimpleNamespace(
        id=11,
        category_id=2,
        title="Gold",
        description="Gold ore",
        quantity=5,
        unit="ton",
    )

    buyer_request = SimpleNamespace(
        id=21,
        buyer_id=user.id,
        listing_id=None,
        title="Gold request",
        description="Test",
        status="OPEN",
        currency="USD",
        target_location="Khartoum",
        created_at=None,
        updated_at=None,
        items=[request_item],
    )

    service = MagicMock(return_value=[buyer_request])
    monkeypatch.setattr(
        requests.RequestService,
        "list_for_buyer",
        service,
    )

    with client:
        response = client.get("/api/v1/requests/mine")

    assert response.status_code == 200, response.text
    assert response.json()[0]["buyer_id"] == user.id
    service.assert_called_once_with(db, buyer_id=user.id, limit=100)


@pytest.mark.parametrize("role", [UserRole.BUYER, UserRole.MERCHANT])
def test_buyer_and_merchant_can_create_offer(role, monkeypatch):
    user = make_user(role)
    client, db = make_client(user)

    item = SimpleNamespace(
        id=31,
        request_item_id=11,
        listing_id=41,
        quantity=2,
        unit_price=Decimal("10"),
        total_price=Decimal("20"),
    )

    offer = SimpleNamespace(
        id=51,
        request_id=21,
        merchant_id=82,
        amount=Decimal("20"),
        currency="USD",
        message="Offer",
        status="PENDING",
        items=[item],
    )

    room = SimpleNamespace(id=61)

    service = MagicMock(return_value=(offer, room))
    monkeypatch.setattr(
        offers.OfferService,
        "create_buyer_offer",
        service,
    )
    monkeypatch.setattr(offers.NotificationService, "create", MagicMock())
    monkeypatch.setattr(
        offers.NotificationService,
        "send_web_push",
        MagicMock(),
    )

    payload = {
        "room_id": 61,
        "currency": "USD",
        "message": "Offer",
        "items": [
            {
                "request_item_id": 11,
                "listing_id": 41,
                "quantity": 2,
                "unit_price": "10",
            }
        ],
    }

    with client:
        response = client.post("/api/v1/offers", json=payload)

    assert response.status_code == 201, response.text
    assert response.json()["id"] == offer.id
    assert response.json()["room_id"] == room.id

    service.assert_called_once()
    assert service.call_args.kwargs["buyer_id"] == user.id
    db.commit.assert_called_once()


@pytest.mark.parametrize("role", [UserRole.BUYER, UserRole.MERCHANT])
def test_buyer_and_merchant_can_accept_offer(role, monkeypatch):
    user = make_user(role)
    client, db = make_client(user)

    room = SimpleNamespace(id=61, status="ACCEPTED")

    service = MagicMock(return_value=room)
    monkeypatch.setattr(
        ui.NegotiationService,
        "accept_offer",
        service,
    )

    db.query.return_value.filter.return_value.first.return_value = None

    with client:
        response = client.post(
            "/api/v1/negotiation/offers/51/accept"
        )

    assert response.status_code == 200, response.text
    assert response.json()["offer_id"] == 51
    assert response.json()["room_id"] == room.id

    service.assert_called_once_with(
        db,
        offer_id=51,
        buyer_id=user.id,
    )


@pytest.mark.parametrize(
    "role",
    [UserRole.ADMIN],
)
@pytest.mark.parametrize(
    "method,path,json_payload",
    [
        ("GET", "/api/v1/requests/mine", None),
        (
            "POST",
            "/api/v1/offers",
            {
                "room_id": 61,
                "items": [
                    {
                        "request_item_id": 11,
                        "quantity": 2,
                        "unit_price": "10",
                    }
                ],
            },
        ),
        ("POST", "/api/v1/negotiation/offers/51/accept", None),
    ],
)
def test_unauthorized_roles_are_rejected(role, method, path, json_payload):
    user = make_user(role)
    client, db = make_client(user)

    with client:
        response = client.request(
            method,
            path,
            json=json_payload,
        )

    assert response.status_code == 403, response.text
    db.commit.assert_not_called()
