"""add notification read state

Revision ID: notification_read_state_20261012
Revises: push_subscriptions_20261011
Create Date: 2026-10-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "notification_read_state_20261012"
down_revision: Union[str, Sequence[str], None] = "push_subscriptions_20261011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_notifications_recipient_read_created",
        "notifications",
        ["recipient_user_id", "read_at", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notifications_recipient_read_created",
        table_name="notifications",
    )
    op.drop_column("notifications", "read_at")
