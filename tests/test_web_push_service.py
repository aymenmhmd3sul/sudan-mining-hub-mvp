from unittest.mock import MagicMock

from app.core.config import settings
from app.services.notification_service import NotificationService


def test_web_push_is_skipped_when_vapid_keys_are_missing(monkeypatch):
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", None)
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", None)

    db = MagicMock()

    result = NotificationService.send_web_push(
        db,
        recipient_user_id=123,
        title="Test notification",
        message="Test message",
        url="/",
    )

    assert result is None
    db.query.assert_not_called()


def test_web_push_continues_after_one_subscription_fails(monkeypatch):
    import sys
    from types import SimpleNamespace

    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "test-public-key")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "test-private-key")
    monkeypatch.setattr(
        settings,
        "VAPID_CLAIMS_EMAIL",
        "mailto:test@example.com",
    )

    subscriptions = [
        SimpleNamespace(
            endpoint="https://push.example.test/first",
            p256dh="first-p256dh",
            auth="first-auth",
        ),
        SimpleNamespace(
            endpoint="https://push.example.test/second",
            p256dh="second-p256dh",
            auth="second-auth",
        ),
    ]

    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = subscriptions

    attempted_endpoints = []

    def fake_webpush(*, subscription_info, **kwargs):
        endpoint = subscription_info["endpoint"]
        attempted_endpoints.append(endpoint)
        if endpoint.endswith("/first"):
            raise RuntimeError("simulated push failure")

    monkeypatch.setitem(
        sys.modules,
        "pywebpush",
        SimpleNamespace(webpush=fake_webpush),
    )

    result = NotificationService.send_web_push(
        db,
        recipient_user_id=123,
        title="Test notification",
        message="Test message",
        url="/",
    )

    assert result is None
    assert attempted_endpoints == [
        "https://push.example.test/first",
        "https://push.example.test/second",
    ]


def test_web_push_forwards_vapid_subscription_and_payload(monkeypatch, tmp_path):
    import json
    import sys
    from types import SimpleNamespace

    private_key = tmp_path / "vapid-private.pem"
    private_key.write_text("test-private-key")

    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "test-public-key")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", str(private_key))
    monkeypatch.setattr(
        settings,
        "VAPID_CLAIMS_EMAIL",
        "mailto:test@example.com",
    )

    subscription = SimpleNamespace(
        endpoint="https://push.example.test/subscription",
        p256dh="test-p256dh",
        auth="test-auth",
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [subscription]

    captured_calls = []

    def fake_webpush(*, subscription_info, data, **kwargs):
        captured_calls.append({
            "subscription_info": subscription_info,
            "data": data,
            **kwargs,
        })

    monkeypatch.setitem(
        sys.modules,
        "pywebpush",
        SimpleNamespace(webpush=fake_webpush),
    )

    result = NotificationService.send_web_push(
        db,
        recipient_user_id=123,
        title="Test title",
        message="Test message",
        url="/buyer/",
    )

    assert result is None
    assert len(captured_calls) == 1

    call = captured_calls[0]
    assert call["vapid_private_key"] == str(private_key)
    assert call["vapid_claims"] == {"sub": "mailto:test@example.com"}
    assert call["subscription_info"] == {
        "endpoint": "https://push.example.test/subscription",
        "keys": {
            "p256dh": "test-p256dh",
            "auth": "test-auth",
        },
    }
    assert json.loads(call["data"]) == {
        "title": "Test title",
        "body": "Test message",
        "url": "/buyer/",
    }
    db.query.assert_called_once()
