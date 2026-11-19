import pytest
from pydantic import ValidationError

from app.schemas.user import UserCreate


@pytest.mark.parametrize("role", ["BUYER", "MERCHANT"])
def test_registration_accepts_supported_roles(role):
    user = UserCreate(
        email="schema-test@example.com",
        password="test-password-only",
        role=role,
    )

    assert user.role.value == role


def test_registration_defaults_to_buyer():
    user = UserCreate(
        email="schema-test@example.com",
        password="test-password-only",
    )

    assert user.role.value == "BUYER"


def test_registration_rejects_removed_agent_role():
    with pytest.raises(ValidationError):
        UserCreate(
            email="schema-test@example.com",
            password="test-password-only",
            role="AGENT",
        )
