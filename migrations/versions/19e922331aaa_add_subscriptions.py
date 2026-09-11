"""add subscriptions

Revision ID: 19e922331aaa
Revises: 482b90e7ab23
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "19e922331aaa"
down_revision: Union[str, Sequence[str], None] = "482b90e7ab23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(length=100), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("renewal_reference", sa.String(length=255), nullable=True),
        sa.Column("payment_reference", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_subscriptions_id",
        "subscriptions",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_user_id",
        "subscriptions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_status",
        "subscriptions",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_id", table_name="subscriptions")
    op.drop_table("subscriptions")
