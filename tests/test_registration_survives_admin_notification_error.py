from unittest.mock import MagicMock

import app.db.base  # noqa: F401 — load the central ORM registry first

import pytest

from app.models.user import UserRole
from app.routers import auth
from app.schemas.user import UserCreate


def test_registration_succeeds_if_admin_notification_raises(monkeypatch):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    def refresh_user(user):
        user.id = 123

    db.refresh.side_effect = refresh_user

    monkeypatch.setattr(
        auth,
        "generate_verification_token",
        lambda: "test-verification-token",
    )
    monkeypatch.setattr(
        auth,
        "hash_verification_token",
        lambda token: "test-token-hash",
    )
    monkeypatch.setattr(
        auth,
        "get_password_hash",
        lambda password: "test-password-hash",
    )
    monkeypatch.setattr(
        auth,
        "send_verification_email",
        lambda email, token: None,
    )

    def fail_notification(*args, **kwargs):
        raise RuntimeError("simulated admin notification failure")

    monkeypatch.setattr(
        auth.NotificationService,
        "notify_admins_of_registration",
        fail_notification,
    )

    user_in = UserCreate(
        email="acceptance-test@example.com",
        password="test-password-only",
        full_name="Acceptance Test",
        role="BUYER",
    )

    result = auth.register_user(user_in, db)

    assert result.id == 123
    assert result.email == "acceptance-test@example.com"
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()
