from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

from app.models.negotiation import NegotiationStatus
from app.routers import ui


@pytest.fixture
def message_route(monkeypatch):
    sender_id = 101
    room_id = 701

    room = SimpleNamespace(
        id=room_id,
        status=NegotiationStatus.OPEN,
    )
    participant = SimpleNamespace(user_id=sender_id)
    message = SimpleNamespace(
        id=9001,
        room_id=room_id,
        sender_id=sender_id,
        body="Test message",
        created_at=datetime.now(timezone.utc),
    )

    db = MagicMock()

    participant_query = MagicMock()
    participant_query.filter.return_value = participant_query
    participant_query.first.return_value = participant

    recipients_query = MagicMock()
    recipients_query.filter.return_value = recipients_query
    recipients_query.all.return_value = [(202,), (303,)]

    db.query.side_effect = [participant_query, recipients_query]

    monkeypatch.setattr(
        ui.NegotiationService,
        "get_room",
        MagicMock(return_value=room),
    )
    monkeypatch.setattr(
        ui.NegotiationService,
        "add_message",
        MagicMock(return_value=message),
    )

    return {
        "db": db,
        "room": room,
        "message": message,
        "sender_id": sender_id,
        "room_id": room_id,
    }


def test_message_creates_notifications_for_other_participants(
    message_route, monkeypatch
):
    create = MagicMock()
    monkeypatch.setattr(ui.NotificationService, "create", create)

    result = ui.send_negotiation_message(
        room_id=message_route["room_id"],
        body="  Test message  ",
        db=message_route["db"],
        user=SimpleNamespace(id=message_route["sender_id"]),
        _subscription_user=None,
    )

    assert result["id"] == message_route["message"].id
    assert result["body"] == "Test message"
    assert [item.kwargs["recipient_user_id"] for item in create.call_args_list] == [
        202,
        303,
    ]
    assert all(
        item.kwargs["event_type"] == "NEGOTIATION_MESSAGE"
        for item in create.call_args_list
    )
    assert message_route["db"].commit.call_count == 1


def test_notification_failure_does_not_fail_message_response(
    message_route, monkeypatch
):
    monkeypatch.setattr(
        ui.NotificationService,
        "create",
        MagicMock(side_effect=RuntimeError("simulated notification failure")),
    )

    result = ui.send_negotiation_message(
        room_id=message_route["room_id"],
        body="Test message",
        db=message_route["db"],
        user=SimpleNamespace(id=message_route["sender_id"]),
        _subscription_user=None,
    )

    assert result["id"] == message_route["message"].id
    assert result["body"] == "Test message"
    message_route["db"].rollback.assert_called_once()
