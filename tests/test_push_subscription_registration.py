from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models.push_subscription import PushSubscription
from app.routers.auth import get_current_user


def _fake_db_dependency(db):
    def dependency():
        yield db
    return dependency


def _install_test_dependencies(db, user):
    app.dependency_overrides[get_db] = _fake_db_dependency(db)
    app.dependency_overrides[get_current_user] = lambda: user


def test_new_push_subscription_is_registered_for_current_user():
    user = SimpleNamespace(id=701)
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    _install_test_dependencies(db, user)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/notifications/push-subscription",
                json={
                    "endpoint": "https://push.example.invalid/subscription-701",
                    "keys": {"p256dh": "public-key-701", "auth": "auth-key-701"},
                },
            )

        assert response.status_code == 200, response.text
        created = db.add.call_args.args[0]
        assert isinstance(created, PushSubscription)
        assert created.user_id == user.id
        assert created.endpoint == "https://push.example.invalid/subscription-701"
        assert created.p256dh == "public-key-701"
        assert created.auth == "auth-key-701"
        db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_existing_push_subscription_can_be_updated_by_its_owner():
    user = SimpleNamespace(id=702)
    existing = SimpleNamespace(
        id=22,
        user_id=user.id,
        endpoint="https://push.example.invalid/subscription-702",
        p256dh="old-public-key",
        auth="old-auth-key",
        updated_at=None,
    )
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = existing

    _install_test_dependencies(db, user)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/notifications/push-subscription",
                json={
                    "endpoint": existing.endpoint,
                    "keys": {"p256dh": "new-public-key", "auth": "new-auth-key"},
                },
            )

        assert response.status_code == 200, response.text
        assert existing.user_id == user.id
        assert existing.p256dh == "new-public-key"
        assert existing.auth == "new-auth-key"
        db.add.assert_not_called()
        db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_push_subscription_cannot_be_reassigned_to_another_user():
    owner = SimpleNamespace(id=703)
    other_user = SimpleNamespace(id=704)
    existing = SimpleNamespace(
        id=23,
        user_id=owner.id,
        endpoint="https://push.example.invalid/subscription-703",
        p256dh="owner-public-key",
        auth="owner-auth-key",
        updated_at=None,
    )
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = existing

    _install_test_dependencies(db, other_user)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/notifications/push-subscription",
                json={
                    "endpoint": existing.endpoint,
                    "keys": {
                        "p256dh": "attacker-public-key",
                        "auth": "attacker-auth-key",
                    },
                },
            )

        assert response.status_code in (403, 409), response.text
        assert existing.user_id == owner.id
        assert existing.p256dh == "owner-public-key"
        assert existing.auth == "owner-auth-key"
        db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()
