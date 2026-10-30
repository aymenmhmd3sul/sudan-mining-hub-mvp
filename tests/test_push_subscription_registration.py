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


def test_unsafe_push_subscription_is_rejected_before_database_query():
    user = SimpleNamespace(id=705)
    db = MagicMock()

    _install_test_dependencies(db, user)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/notifications/push-subscription",
                json={
                    "endpoint": "http://127.0.0.1/internal",
                    "keys": {
                        "p256dh": "public-key-705",
                        "auth": "auth-key-705",
                    },
                },
            )

        assert response.status_code == 422, response.text
        db.query.assert_not_called()
        db.add.assert_not_called()
        db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


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
                    "language": "en",
                },
            )

        assert response.status_code == 200, response.text
        created = db.add.call_args.args[0]
        assert isinstance(created, PushSubscription)
        assert created.user_id == user.id
        assert created.endpoint == "https://push.example.invalid/subscription-701"
        assert created.p256dh == "public-key-701"
        assert created.auth == "auth-key-701"
        assert created.language == "en"
        db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_existing_push_subscription_can_be_updated_by_its_owner():
    user = SimpleNamespace(id=702)
    existing = SimpleNamespace(
        id=22,
        user_id=user.id,
        endpoint="https://push.example.invalid/subscription-702",
        language="ar",
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
                    "language": "en",
                },
            )

        assert response.status_code == 200, response.text
        assert existing.user_id == user.id
        assert existing.p256dh == "new-public-key"
        assert existing.auth == "new-auth-key"
        assert existing.language == "en"
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


def test_mark_notification_read_hides_negotiation_sender_and_message():
    from datetime import datetime, timezone

    user = SimpleNamespace(id=701)
    notification = SimpleNamespace(
        id=81,
        recipient_user_id=user.id,
        event_type="NEGOTIATION_MESSAGE",
        title="Private sender name",
        message="Confidential negotiation text",
        related_type="NEGOTIATION_ROOM",
        related_id=900,
        event_key="malformed-event-key",
        created_at=datetime.now(timezone.utc),
        read_at=None,
    )
    db = MagicMock()
    notification_query = MagicMock()
    notification_query.filter.return_value = notification_query
    notification_query.first.return_value = notification
    db.query.return_value = notification_query

    _install_test_dependencies(db, user)
    try:
        with TestClient(app) as client:
            response = client.patch(
                "/api/notifications/81/read",
                cookies={"language": "en"},
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ok"] is True
        payload = body["notification"]

        assert payload["title"] == "New message"
        assert payload["message"] == "New message"
        assert "Private sender name" not in response.text
        assert "Confidential negotiation text" not in response.text
        assert notification.read_at is not None
        db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_localized_notification_hides_negotiation_room_with_unexpected_event_type():
    from datetime import datetime, timezone

    from app.routers.notifications import _localized_notification_payload

    notification = SimpleNamespace(
        id=83,
        event_type="UNEXPECTED_EVENT_TYPE",
        title="Private sender name",
        message="Confidential negotiation text",
        related_type="NEGOTIATION_ROOM",
        related_id=900,
        created_at=datetime.now(timezone.utc),
        read_at=None,
    )

    payload = _localized_notification_payload(notification, "en")

    assert payload["title"] == "New message"
    assert payload["message"] == "New message"
    assert "Private sender name" not in str(payload)
    assert "Confidential negotiation text" not in str(payload)

def test_list_notifications_hides_negotiation_sender_and_message_with_malformed_event_key():
    from datetime import datetime, timezone

    user = SimpleNamespace(id=701)
    notification = SimpleNamespace(
        id=82,
        recipient_user_id=user.id,
        event_type="NEGOTIATION_MESSAGE",
        title="Private sender name",
        message="Confidential negotiation text",
        related_type="UNEXPECTED_TYPE",
        related_id=900,
        event_key="malformed-event-key",
        created_at=datetime.now(timezone.utc),
        read_at=None,
    )

    db = MagicMock()
    count_query = MagicMock()
    notification_query = MagicMock()

    count_query.filter.return_value = count_query
    count_query.scalar.return_value = 1

    notification_query.filter.return_value = notification_query
    notification_query.order_by.return_value = notification_query
    notification_query.limit.return_value = notification_query
    notification_query.all.return_value = [notification]

    db.query.side_effect = [count_query, notification_query]

    _install_test_dependencies(db, user)
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/notifications",
                cookies={"language": "en"},
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["unread_count"] == 1
        assert len(body["items"]) == 1

        payload = body["items"][0]
        assert payload["title"] == "New message"
        assert payload["message"] == "New message"
        assert "Private sender name" not in response.text
        assert "Confidential negotiation text" not in response.text
    finally:
        app.dependency_overrides.clear()
