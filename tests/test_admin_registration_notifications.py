from unittest.mock import MagicMock, call

from app.models.user import UserModel, UserRole
from app.services.notification_service import NotificationService


def test_registration_notifies_every_admin(monkeypatch):
    admins = [
        MagicMock(id=10),
        MagicMock(id=20),
    ]

    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = admins

    create_mock = MagicMock()
    push_mock = MagicMock()

    monkeypatch.setattr(NotificationService, "create", create_mock)
    monkeypatch.setattr(NotificationService, "send_web_push", push_mock)

    NotificationService.notify_admins_of_registration(
        db,
        registered_user_id=123,
        registered_user_email="new-user@example.com",
    )

    assert db.query.call_args == call(UserModel)
    assert db.query.return_value.filter.call_args.args[0].left.name == "role"
    assert db.query.return_value.filter.call_args.args[0].right.value == UserRole.ADMIN.value

    assert [item.kwargs["recipient_user_id"] for item in create_mock.call_args_list] == [
        10,
        20,
    ]
    assert all(
        item.kwargs["event_type"] == "admin_new_registration"
        for item in create_mock.call_args_list
    )
    assert db.commit.call_count == 1
    assert push_mock.call_count == 2


def test_notification_failure_does_not_escape_registration_helper(monkeypatch):
    admins = [MagicMock(id=10)]

    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = admins

    create_mock = MagicMock(side_effect=RuntimeError("notification failure"))
    push_mock = MagicMock()

    monkeypatch.setattr(NotificationService, "create", create_mock)
    monkeypatch.setattr(NotificationService, "send_web_push", push_mock)

    # The helper must absorb the notification error; registration already
    # committed the user before this helper is called.
    NotificationService.notify_admins_of_registration(
        db,
        registered_user_id=123,
        registered_user_email="new-user@example.com",
    )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()
    push_mock.assert_not_called()
