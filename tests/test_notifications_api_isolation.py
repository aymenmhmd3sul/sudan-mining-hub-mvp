from types import SimpleNamespace
from unittest.mock import MagicMock

import app.db.base  # noqa: F401
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.models.notification import Notification
from app.routers.auth import get_current_user


def _fake_db_dependency(db):
    def dependency():
        yield db
    return dependency


def test_notifications_require_authentication_without_real_database():
    fake_db = MagicMock()
    app.dependency_overrides[get_db] = _fake_db_dependency(fake_db)
    try:
        with TestClient(app) as client:
            response = client.get("/api/notifications")

        assert response.status_code == 401, response.text
        fake_db.query.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_user_cannot_mark_another_users_notification_as_read():
    user = SimpleNamespace(id=101)
    fake_db = MagicMock()
    query = fake_db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    app.dependency_overrides[get_db] = _fake_db_dependency(fake_db)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            response = client.patch("/api/notifications/9001/read")

        assert response.status_code == 404, response.text
        fake_db.commit.assert_not_called()
        query.filter.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_notification_list_is_scoped_to_authenticated_user():
    user = SimpleNamespace(id=202)
    fake_db = MagicMock()

    count_query = MagicMock()
    count_query.filter.return_value = count_query
    count_query.scalar.return_value = 0

    items_query = MagicMock()
    items_query.filter.return_value = items_query
    items_query.order_by.return_value = items_query
    items_query.limit.return_value = items_query
    items_query.all.return_value = []

    fake_db.query.side_effect = [count_query, items_query]

    app.dependency_overrides[get_db] = _fake_db_dependency(fake_db)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as client:
            response = client.get("/api/notifications")

        assert response.status_code == 200, response.text
        assert response.json() == {"unread_count": 0, "items": []}

        count_filter = count_query.filter.call_args.args[0]
        items_filter = items_query.filter.call_args.args[0]
        assert count_filter.left.name == "recipient_user_id"
        assert count_filter.right.value == user.id
        assert items_filter.left.name == "recipient_user_id"
        assert items_filter.right.value == user.id
    finally:
        app.dependency_overrides.clear()
