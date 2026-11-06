from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.db.base  # noqa: F401 - register all ORM relationships without DB access
from app.db.session import get_db
from app.models.buyer_request import BuyerRequest
from app.models.listing import ListingStatus
from app.models.negotiation import NegotiationRoom
from app.models.user import UserRole
from app.routers.auth import get_current_user, require_active_subscription
from app.routers import ui


app = FastAPI()
app.include_router(ui.router)


class FakeQuery:
    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return None


class FakeDB:
    def __init__(self):
        self.added = []
        self.next_id = 1
        self.commits = 0
        self.rollbacks = 0

    def query(self, model):
        self.queried = True
        return FakeQuery()

    def add(self, instance):
        self.added.append(instance)

    def add_all(self, instances):
        self.added.extend(instances)

    def flush(self):
        for instance in self.added:
            if getattr(instance, "id", None) is None:
                instance.id = self.next_id
                self.next_id += 1

    def commit(self):
        self.commits += 1

    def refresh(self, instance):
        return None

    def rollback(self):
        self.rollbacks += 1


def _client_for_authenticated_user(user):
    db = FakeDB()

    def override_db():
        return db

    def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[require_active_subscription] = lambda: user
    return TestClient(app), db


def _client_for_unauthenticated_user():
    db = FakeDB()

    def override_db():
        return db

    app.dependency_overrides[get_db] = override_db
    # Keep get_current_user and require_role real: no cookie must fail authentication.
    return TestClient(app), db


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def _active_listing():
    return SimpleNamespace(
        id=41,
        status=ListingStatus.ACTIVE,
        is_negotiable=True,
        owner_id=82,
        title="Gold ore",
        description="Sample listing",
        currency="USD",
        category_id=7,
        locations=[],
    )


def test_buyer_can_start_eligible_negotiation_without_database():
    buyer = SimpleNamespace(id=13, role=UserRole.BUYER)
    client, db = _client_for_authenticated_user(buyer)

    with (
        patch("app.routers.ui.ListingService.get_by_id", return_value=_active_listing()),
        patch("app.routers.ui.ListingService.require_quantity_classified"),
        client,
    ):
        response = client.post("/api/v1/listings/41/negotiate")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["listing_id"] == 41
    assert payload["existing"] is False
    assert any(isinstance(item, BuyerRequest) for item in db.added)
    assert any(isinstance(item, NegotiationRoom) for item in db.added)
    assert db.commits == 1


@pytest.mark.parametrize("role", [UserRole.MERCHANT, UserRole.AGENT])
def test_non_buyer_cannot_start_negotiation_or_create_records(role):
    client, db = _client_for_authenticated_user(SimpleNamespace(id=13, role=role))

    with client:
        response = client.post("/api/v1/listings/41/negotiate")

    assert response.status_code == 403, response.text
    assert not any(isinstance(item, (BuyerRequest, NegotiationRoom)) for item in db.added)
    assert db.commits == 0


def test_unauthenticated_user_cannot_start_negotiation_or_create_records():
    client, db = _client_for_unauthenticated_user()

    with client:
        response = client.post("/api/v1/listings/41/negotiate")

    assert response.status_code == 401, response.text
    assert not any(isinstance(item, (BuyerRequest, NegotiationRoom)) for item in db.added)
    assert db.commits == 0
    assert not getattr(db, "queried", False)

