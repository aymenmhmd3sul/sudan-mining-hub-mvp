from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.models.negotiation import (
    NegotiationParticipant,
    NegotiationStatus,
)
from app.models.buyer_request import BuyerRequest
from app.models.listing import Listing
from app.models.offer import Offer
from app.routers import ui


@pytest.fixture
def agent_message_route(monkeypatch):
    agent_id = 101

    room = SimpleNamespace(
        id=701,
        request_id=801,
        offer_id=None,
        status=NegotiationStatus.OPEN,
    )

    participant = SimpleNamespace(user_id=agent_id)

    participant_query = MagicMock()
    participant_query.filter.return_value = participant_query
    participant_query.first.return_value = participant

    request_query = MagicMock()
    request_query.filter.return_value = request_query

    listing_query = MagicMock()
    listing_query.filter.return_value = listing_query

    offer_query = MagicMock()
    offer_query.filter.return_value = offer_query

    recipients_query = MagicMock()
    recipients_query.filter.return_value = recipients_query
    recipients_query.all.return_value = []

    db = MagicMock()
    participant_calls = 0

    def query_dispatch(model):
        nonlocal participant_calls

        if (
            model is NegotiationParticipant
            or model is NegotiationParticipant.user_id
        ):
            participant_calls += 1
            if participant_calls == 1:
                return participant_query
            return recipients_query

        if model is BuyerRequest:
            return request_query

        if model is Listing:
            return listing_query

        if model is Offer:
            return offer_query

        raise AssertionError(f"Unexpected query model: {model}")

    db.query.side_effect = query_dispatch

    monkeypatch.setattr(
        ui.NegotiationService,
        "get_room",
        MagicMock(return_value=room),
    )

    add_message = MagicMock(
        return_value=SimpleNamespace(
            id=9001,
            room_id=room.id,
            sender_id=agent_id,
            body="Test message",
            created_at=None,
        )
    )
    monkeypatch.setattr(
        ui.NegotiationService,
        "add_message",
        add_message,
    )
    monkeypatch.setattr(
        ui.NotificationService,
        "create",
        MagicMock(),
    )
    monkeypatch.setattr(
        ui.NotificationService,
        "send_web_push",
        MagicMock(),
    )

    return {
        "agent_id": agent_id,
        "room": room,
        "db": db,
        "request_query": request_query,
        "listing_query": listing_query,
        "offer_query": offer_query,
        "add_message": add_message,
    }


def test_unapproved_agent_can_send_message_as_buyer(
    agent_message_route,
):
    ctx = agent_message_route
    ctx["request_query"].first.return_value = SimpleNamespace(
        buyer_id=ctx["agent_id"],
        listing_id=901,
    )
    ctx["listing_query"].first.return_value = SimpleNamespace(
        id=901,
        owner_id=202,
    )

    result = ui.send_negotiation_message(
        room_id=ctx["room"].id,
        body="Test message",
        db=ctx["db"],
        user=SimpleNamespace(
            id=ctx["agent_id"],
            role="AGENT",
            is_approved=False,
        ),
        _subscription_user=None,
    )

    assert result["id"] == 9001
    ctx["add_message"].assert_called_once()


def test_unapproved_agent_cannot_send_message_as_listing_owner(
    agent_message_route,
):
    ctx = agent_message_route
    ctx["request_query"].first.return_value = SimpleNamespace(
        buyer_id=202,
        listing_id=901,
    )
    ctx["listing_query"].first.return_value = SimpleNamespace(
        id=901,
        owner_id=ctx["agent_id"],
    )

    with pytest.raises(HTTPException) as exc:
        ui.send_negotiation_message(
            room_id=ctx["room"].id,
            body="Test message",
            db=ctx["db"],
            user=SimpleNamespace(
                id=ctx["agent_id"],
                role="AGENT",
                is_approved=False,
            ),
            _subscription_user=None,
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Seller approval required"
    ctx["add_message"].assert_not_called()


def test_unapproved_agent_can_send_message_as_buyer_in_offer_room(
    agent_message_route,
):
    ctx = agent_message_route
    ctx["room"].offer_id = 902
    ctx["request_query"].first.return_value = None
    ctx["offer_query"].first.return_value = SimpleNamespace(
        id=902,
        merchant_id=202,
    )

    result = ui.send_negotiation_message(
        room_id=ctx["room"].id,
        body="Test message",
        db=ctx["db"],
        user=SimpleNamespace(
            id=ctx["agent_id"],
            role="AGENT",
            is_approved=False,
        ),
        _subscription_user=None,
    )

    assert result["id"] == 9001
    ctx["add_message"].assert_called_once()


def test_unapproved_agent_cannot_send_message_as_offer_merchant(
    agent_message_route,
):
    ctx = agent_message_route
    ctx["room"].offer_id = 902
    ctx["request_query"].first.return_value = None
    ctx["offer_query"].first.return_value = SimpleNamespace(
        id=902,
        merchant_id=ctx["agent_id"],
    )

    with pytest.raises(HTTPException) as exc:
        ui.send_negotiation_message(
            room_id=ctx["room"].id,
            body="Test message",
            db=ctx["db"],
            user=SimpleNamespace(
                id=ctx["agent_id"],
                role="AGENT",
                is_approved=False,
            ),
            _subscription_user=None,
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Seller approval required"
    ctx["add_message"].assert_not_called()


def test_missing_request_blocks_message_sending(agent_message_route):
    ctx = agent_message_route
    ctx["request_query"].first.return_value = None

    with pytest.raises(HTTPException) as exc:
        ui.send_negotiation_message(
            room_id=ctx["room"].id,
            body="Test message",
            db=ctx["db"],
            user=SimpleNamespace(
                id=ctx["agent_id"],
                role="AGENT",
                is_approved=False,
            ),
            _subscription_user=None,
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Negotiation request not found"
    ctx["add_message"].assert_not_called()
