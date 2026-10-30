from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.routers.ui import get_optional_current_user


def _fake_db_dependency(db):
    def dependency():
        yield db
    return dependency


def test_missing_negotiation_room_returns_404_without_database_access():
    user = SimpleNamespace(id=101)
    fake_db = MagicMock()

    app.dependency_overrides[get_db] = _fake_db_dependency(fake_db)
    app.dependency_overrides[get_optional_current_user] = lambda: user

    try:
        with patch(
            "app.routers.ui.NegotiationService.get_room",
            return_value=None,
        ):
            with TestClient(app) as client:
                response = client.get("/negotiation?room_id=701")

        assert response.status_code == 404, response.text
        fake_db.query.assert_not_called()
        fake_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_non_participant_cannot_open_negotiation_room():
    user = SimpleNamespace(id=101)
    room = SimpleNamespace(id=701)
    fake_db = MagicMock()

    participant_query = fake_db.query.return_value
    participant_query.filter.return_value = participant_query
    participant_query.first.return_value = None

    app.dependency_overrides[get_db] = _fake_db_dependency(fake_db)
    app.dependency_overrides[get_optional_current_user] = lambda: user

    try:
        with patch(
            "app.routers.ui.NegotiationService.get_room",
            return_value=room,
        ):
            with TestClient(app) as client:
                response = client.get("/negotiation?room_id=701")

        assert response.status_code == 403, response.text
        fake_db.commit.assert_not_called()
        participant_query.first.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_authorized_participant_can_load_negotiation_messages_after_access_check():
    from starlette.requests import Request
    from app.models.negotiation import (
        NegotiationParticipant,
        NegotiationMessage,
        NegotiationRoom,
        NegotiationStatus,
    )
    from app.routers.ui import negotiation_page

    user = SimpleNamespace(
        id=101,
        role=SimpleNamespace(value="BUYER"),
    )
    room = SimpleNamespace(
        id=701,
        status=NegotiationStatus.OPEN,
        merchant_approved_at=None,
        request=None,
        offer=None,
    )
    participant = SimpleNamespace(last_read_at=None)
    other_room_last_read_at = object()
    other_room_participant = SimpleNamespace(
        last_read_at=other_room_last_read_at
    )
    inbox_room = SimpleNamespace(
        id=702,
        updated_at=None,
        status=NegotiationStatus.OPEN,
    )
    message = SimpleNamespace(
        id=8801,
        room_id=701,
        sender_id=202,
        body="authorized message",
        created_at=None,
    )

    participant_query = MagicMock()
    participant_query.filter.return_value = participant_query
    participant_query.first.side_effect = [
        participant,
        other_room_participant,
    ]

    inbox_query = MagicMock()
    inbox_query.join.return_value = inbox_query
    inbox_query.filter.return_value = inbox_query
    inbox_query.order_by.return_value = inbox_query
    inbox_query.all.return_value = [inbox_room]

    unread_query = MagicMock()
    unread_query.filter.return_value = unread_query
    unread_query.count.return_value = 3

    message_query = MagicMock()
    message_query.filter.return_value = message_query
    message_query.order_by.return_value = message_query
    message_query.all.return_value = [message]

    active_query = MagicMock()
    active_query.filter.return_value = active_query
    active_query.count.return_value = 0

    events = []
    room_query_calls = 0
    message_query_calls = 0

    def query_for(model):
        nonlocal room_query_calls, message_query_calls

        if model is NegotiationParticipant:
            events.append("participant_lookup")
            return participant_query

        if model is NegotiationRoom:
            room_query_calls += 1
            if room_query_calls == 1:
                events.append("inbox_query")
                return inbox_query
            events.append("active_rooms_query")
            return active_query

        if model is NegotiationMessage:
            message_query_calls += 1
            if message_query_calls == 1:
                events.append("unread_count_query")
                return unread_query
            assert "commit" in events, (
                "Messages were queried before the participant access check was committed"
            )
            events.append("messages_query")
            return message_query

        raise AssertionError(f"Unexpected database query model: {model}")

    fake_db = MagicMock()
    fake_db.query.side_effect = query_for
    fake_db.commit.side_effect = lambda: events.append("commit")

    request = Request({
        "type": "http",
        "method": "GET",
        "scheme": "http",
        "path": "/negotiation",
        "query_string": b"room_id=701",
        "headers": [],
    })

    expected_response = object()
    template_response = MagicMock(return_value=expected_response)

    with (
        patch(
            "app.routers.ui.NegotiationService.get_room",
            return_value=room,
        ),
        patch(
            "app.routers.ui.template_context",
            return_value={"t": lambda key: key},
        ),
        patch(
            "app.routers.ui.templates.TemplateResponse",
            template_response,
        ),
    ):
        response = negotiation_page(
            request=request,
            room_id=701,
            db=fake_db,
            user=user,
        )

    assert response is expected_response

    def predicates(call):
        return [
            (
                clause.left.key,
                clause.right.value,
                clause.operator.__name__,
            )
            for clause in call.args
        ]

    # The room access check must bind both the requested room and current user.
    assert predicates(participant_query.filter.call_args_list[0]) == [
        ("room_id", 701, "eq"),
        ("user_id", 101, "eq"),
    ]

    # The inbox participant lookup must be scoped to the candidate room and user.
    assert predicates(participant_query.filter.call_args_list[1]) == [
        ("room_id", 702, "eq"),
        ("user_id", 101, "eq"),
    ]

    # The room list itself must be restricted to the current user's participation.
    assert predicates(inbox_query.filter.call_args_list[0]) == [
        ("user_id", 101, "eq"),
    ]

    # Unread messages must belong to this room and come from another user.
    assert predicates(unread_query.filter.call_args_list[0]) == [
        ("room_id", 702, "eq"),
        ("sender_id", 101, "ne"),
    ]

    # The read-time boundary must also be applied to the unread count.
    assert predicates(unread_query.filter.call_args_list[1]) == [
        ("created_at", other_room_last_read_at, "gt"),
    ]

    assert participant.last_read_at is not None
    assert other_room_participant.last_read_at is other_room_last_read_at
    fake_db.commit.assert_called_once()
    message_query.all.assert_called_once()

    assert events.index("commit") < events.index("messages_query")

    template_response.assert_called_once()
    context = template_response.call_args.kwargs["context"]
    assert context["room"] is room
    assert context["messages"] == [message]
    assert context["inbox_rooms"] == [
        {"room": inbox_room, "unread_count": 3}
    ]
    assert set(context["inbox_rooms"][0]) == {"room", "unread_count"}
    assert participant_query.first.call_count == 2
    unread_query.count.assert_called_once()
