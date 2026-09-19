"""add notifications

Revision ID: 16e79180eb65
Revises: d16f79_subscription_status_enum
Create Date: 2026-09-19
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql
import sqlalchemy as sa


revision: str = "16e79180eb65"
down_revision: Union[str, Sequence[str], None] = "d16f79_subscription_status_enum"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    notification_channel = postgresql.ENUM(
        "IN_APP",
        "EMAIL",
        "WHATSAPP",
        name="notificationchannel",
        create_type=False,
    )
    notification_status = postgresql.ENUM(
        "PENDING",
        "SENT",
        "FAILED",
        name="notificationstatus",
        create_type=False,
    )

    notification_channel.create(op.get_bind(), checkfirst=True)
    notification_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recipient_user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column(
            "channel",
            notification_channel,
            nullable=False,
        ),
        sa.Column(
            "status",
            notification_status,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("related_type", sa.String(length=100), nullable=True),
        sa.Column("related_id", sa.Integer(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_notifications_id",
        "notifications",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_recipient_user_id",
        "notifications",
        ["recipient_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_event_type",
        "notifications",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_channel",
        "notifications",
        ["channel"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_status",
        "notifications",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_recipient_created",
        "notifications",
        ["recipient_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_related",
        "notifications",
        ["related_type", "related_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_related", table_name="notifications")
    op.drop_index(
        "ix_notifications_recipient_created",
        table_name="notifications",
    )
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_channel", table_name="notifications")
    op.drop_index("ix_notifications_event_type", table_name="notifications")
    op.drop_index(
        "ix_notifications_recipient_user_id",
        table_name="notifications",
    )
    op.drop_index("ix_notifications_id", table_name="notifications")
    op.drop_table("notifications")

    notification_status = postgresql.ENUM(
        "PENDING",
        "SENT",
        "FAILED",
        name="notificationstatus",
        create_type=False,
    )
    notification_channel = postgresql.ENUM(
        "IN_APP",
        "EMAIL",
        "WHATSAPP",
        name="notificationchannel",
        create_type=False,
    )

    notification_status.drop(op.get_bind(), checkfirst=True)
    notification_channel.drop(op.get_bind(), checkfirst=True)
