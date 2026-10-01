"""add notification event key for idempotency

Revision ID: notification_idempotency_20261001
Revises: cps_pay_settings_20261001
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "notif_idem_20261001"
down_revision: Union[str, Sequence[str], None] = "cps_pay_settings_20261001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column(
            "event_key",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_unique_constraint(
        "uq_notifications_event_key",
        "notifications",
        ["event_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_notifications_event_key",
        "notifications",
        type_="unique",
    )
    op.drop_column("notifications", "event_key")
