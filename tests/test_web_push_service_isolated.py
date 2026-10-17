import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock

from app.core.config import settings
from app.services.notification_service import NotificationService


def test_web_push_passes_subscription_payload_and_vapid(monkeypatch):
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "test-public-key")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "test-private-key")
    monkeypatch.setattr(
        settings,
        "VAPID_CLAIMS_EMAIL",
        "mailto:test@example.com",
    )

    subscription = SimpleNamespace(
        endpoint="https://push.example.invalid/test-endpoint",
        p256dh="test-p256dh",
        auth="test-auth",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [subscription]

    provider = ModuleType("pywebpush")
    provider.webpush = MagicMock()
    monkeypatch.setitem(sys.modules, "pywebpush", provider)

    result = NotificationService.send_web_push(
        db,
        recipient_user_id=123,
        title="Test title",
        message="Test message",
        url="/test-target",
    )

    assert result is None
    db.query.assert_called_once()
    provider.webpush.assert_called_once()

    kwargs = provider.webpush.call_args.kwargs
    assert kwargs["subscription_info"] == {
        "endpoint": subscription.endpoint,
        "keys": {
            "p256dh": subscription.p256dh,
            "auth": subscription.auth,
        },
    }
    assert json.loads(kwargs["data"]) == {
        "title": "Test title",
        "body": "Test message",
        "url": "/test-target",
    }
    assert kwargs["vapid_private_key"] == "test-private-key"
    assert kwargs["vapid_claims"] == {"sub": "mailto:test@example.com"}


def test_web_push_failure_does_not_escape(monkeypatch):
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", "test-public-key")
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "test-private-key")

    subscription = SimpleNamespace(
        endpoint="https://push.example.invalid/failing-endpoint",
        p256dh="test-p256dh",
        auth="test-auth",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [subscription]

    provider = ModuleType("pywebpush")
    provider.webpush = MagicMock(side_effect=RuntimeError("simulated provider failure"))
    monkeypatch.setitem(sys.modules, "pywebpush", provider)

    monkeypatch.setattr(
        "app.services.notification_service.logger.exception",
        MagicMock(),
    )

    result = NotificationService.send_web_push(
        db,
        recipient_user_id=123,
        title="Failure test",
        message="Simulated failure",
    )

    assert result is None
    provider.webpush.assert_called_once()


def test_web_push_is_skipped_when_vapid_keys_are_missing(monkeypatch):
    monkeypatch.setattr(settings, "VAPID_PUBLIC_KEY", None)
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", None)

    db = MagicMock()
    result = NotificationService.send_web_push(
        db,
        recipient_user_id=123,
        title="Skipped test",
        message="No VAPID keys",
    )

    assert result is None
    db.query.assert_not_called()
