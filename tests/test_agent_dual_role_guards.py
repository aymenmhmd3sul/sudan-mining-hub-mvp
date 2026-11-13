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

from fastapi.routing import APIRoute
from app.routers import ui


def _route_role_guard(path):
    route = next(
        (
            item for item in ui.router.routes
            if isinstance(item, APIRoute) and item.path == path
        ),
        None,
    )
    assert route is not None, f"Route not found: {path}"

    for dependency in route.dependant.dependencies:
        guard = dependency.call
        if getattr(guard, "__name__", "") not in {
            "role_guard", "seller_guard"
        }:
            continue

        allowed_roles = next(
            (
                cell.cell_contents
                for cell in (guard.__closure__ or ())
                if isinstance(cell.cell_contents, tuple)
                and all(isinstance(role, str) for role in cell.cell_contents)
            ),
            None,
        )
        if allowed_roles is not None:
            return guard.__name__, allowed_roles

    raise AssertionError(f"Role guard not found for {path}")


@pytest.mark.parametrize(
    ("path", "expected_guard", "expected_roles"),
    [
        (
            "/api/v1/negotiation/offers/{offer_id}/finalize",
            "seller_guard",
            ("MERCHANT", "AGENT"),
        ),
        (
            "/api/v1/negotiation/offers/{offer_id}/accept",
            "role_guard",
            ("BUYER", "AGENT"),
        ),
        (
            "/api/v1/negotiation/{room_id}/messages",
            "role_guard",
            ("BUYER", "MERCHANT", "AGENT"),
        ),
    ],
)
def test_agent_negotiation_route_role_contracts(
    path, expected_guard, expected_roles
):
    assert _route_role_guard(path) == (expected_guard, expected_roles)

from app.routers.ui import _require_agent_seller_approval


def test_agent_message_approval_depends_on_seller_identity():
    unapproved_agent = SimpleNamespace(
        id=13,
        role=UserRole.AGENT,
        is_approved=False,
    )

    # Agent acting as buyer: seller approval is not required.
    assert _require_agent_seller_approval(
        unapproved_agent, listing_owner_id=27
    ) is unapproved_agent

    # Agent acting as listing owner: approval is mandatory.
    with pytest.raises(HTTPException) as exc:
        _require_agent_seller_approval(
            unapproved_agent, listing_owner_id=13
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Seller approval required"


def test_approved_agent_can_message_as_listing_owner():
    approved_agent = SimpleNamespace(
        id=13,
        role=UserRole.AGENT,
        is_approved=True,
    )

    assert _require_agent_seller_approval(
        approved_agent, listing_owner_id=13
    ) is approved_agent
