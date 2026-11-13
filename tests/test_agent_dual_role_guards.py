from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

import app.db.base  # noqa: F401
from app.models.user import UserRole
from app.routers.auth import require_seller_role
from app.routers.requests import require_agent_active_subscription


@pytest.mark.parametrize("role", [UserRole.AGENT, UserRole.MERCHANT])
def test_unapproved_seller_is_rejected(role):
    user = SimpleNamespace(
        id=13,
        role=role,
        is_approved=False,
    )

    guard = require_seller_role("MERCHANT", "AGENT")

    with pytest.raises(HTTPException) as exc:
        guard(user)

    assert exc.value.status_code == 403


def test_approved_agent_passes_seller_guard():
    user = SimpleNamespace(
        id=13,
        role=UserRole.AGENT,
        is_approved=True,
    )

    guard = require_seller_role("MERCHANT", "AGENT")

    assert guard(user) is user


def test_agent_without_active_subscription_is_rejected():
    user = SimpleNamespace(id=13, role=UserRole.AGENT)
    db = object()

    with patch(
        "app.routers.requests.SubscriptionService.is_active",
        return_value=False,
    ):
        with pytest.raises(HTTPException) as exc:
            require_agent_active_subscription(db, user)

    assert exc.value.status_code == 403
    assert exc.value.detail == "Active subscription required"


def test_agent_with_active_subscription_is_allowed():
    user = SimpleNamespace(id=13, role=UserRole.AGENT)
    db = object()

    with patch(
        "app.routers.requests.SubscriptionService.is_active",
        return_value=True,
    ):
        assert require_agent_active_subscription(db, user) is user


def test_merchant_subscription_behavior_is_unchanged():
    user = SimpleNamespace(id=13, role=UserRole.MERCHANT)
    db = object()

    with patch(
        "app.routers.requests.SubscriptionService.is_active",
    ) as subscription_check:
        assert require_agent_active_subscription(db, user) is user

    subscription_check.assert_not_called()
