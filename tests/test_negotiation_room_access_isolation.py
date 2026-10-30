from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.routers.ui import get_optional_current_user
from app.models.negotiation import NegotiationParticipant


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
                response = client.get("/negotiation?room_id=9001")

        assert response.status_code == 404, response.text
        fake_db.query.assert_not_called()
        fake_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()


def test_nonparticipant_cannot_open_negotiation_room():
    user = SimpleNamespace(id=101)
    room = SimpleNamespace(id=701)
    fake_db = MagicMock()

    query = fake_db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

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
        fake_db.query.assert_called_once_with(NegotiationParticipant)
        fake_db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()
