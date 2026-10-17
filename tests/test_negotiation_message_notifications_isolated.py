from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models.negotiation import NegotiationParticipant, NegotiationStatus
from app.models.notification import NotificationChannel
from app.routers import ui


def make_test_context():
    db = MagicMock()
    room = SimpleNamespace(id=77, status=NegotiationStatus.OPEN)
    user = SimpleNamespace(id=11)
    message = SimpleNamespace(
        id=501,
        room_id=77,
        sender_id=11,
        body="Test negotiation message",
        created_at=None,
    )

    participant_query = MagicMock()
    participant_query.filter.return_value.first.return_value = SimpleNamespace(
        user_id=11
    )

    recipient_query = MagicMock()
    recipient_query.filter.return_value.all.return_value = [
        SimpleNamespace(user_id=22)
    ]

    db.query.side_effect = [participant_query, recipient_query]

    return db, room, user, message


def test_message_creates_in_app_notification_and_attempts_push(monkeypatch):
    db, room, user, message = make_test_context()

    monkeypatch.setattr(ui.NegotiationService, "get_room", lambda db, room_id: room)
    monkeypatch.setattr(
        ui.NegotiationService,
        "add_message",
        lambda db, **kwargs: message,
    )
    create = MagicMock()
    push = MagicMock()
    monkeypatch.setattr(ui.NotificationService, "create", create)
    monkeypatch.setattr(ui.NotificationService, "send_web_push", push)

    result = ui.send_negotiation_message(
        room_id=77,
        body="  Test negotiation message  ",
        db=db,
        user=user,
    )

    assert result["id"] == message.id
    assert result["body"] == message.body

    create.assert_called_once_with(
        db,
        recipient_user_id=22,
        event_type="NEGOTIATION_MESSAGE",
        title="رسالة تفاوض جديدة",
        message="لديك رسالة جديدة في غرفة التفاوض.",
        channel=NotificationChannel.IN_APP,
        related_type="negotiation_message",
        related_id=message.id,
        event_key="negotiation_message:501:22",
    )
    db.commit.assert_called_once()
    push.assert_called_once_with(
        db,
        recipient_user_id=22,
        title="رسالة تفاوض جديدة",
        message="لديك رسالة جديدة في غرفة التفاوض.",
        url="/negotiation?room_id=77",
    )


def test_notification_failure_does_not_fail_saved_message(monkeypatch):
    db, room, user, message = make_test_context()

    monkeypatch.setattr(ui.NegotiationService, "get_room", lambda db, room_id: room)
    monkeypatch.setattr(
        ui.NegotiationService,
        "add_message",
        lambda db, **kwargs: message,
    )
    monkeypatch.setattr(
        ui.NotificationService,
        "create",
        MagicMock(side_effect=RuntimeError("simulated notification failure")),
    )
    monkeypatch.setattr(ui.logger, "exception", MagicMock())

    result = ui.send_negotiation_message(
        room_id=77,
        body="Test negotiation message",
        db=db,
        user=user,
    )

    assert result["id"] == message.id
    db.rollback.assert_called_once()
    db.commit.assert_not_called()
