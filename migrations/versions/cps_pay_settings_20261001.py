"""add independent commission payment settings

Revision ID: cps_pay_settings_20261001
Revises: cps_payment_20261001
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cps_pay_settings_20261001"
down_revision: Union[str, Sequence[str], None] = "cps_payment_20261001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commission_payment_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("account_number", sa.String(length=255), nullable=True),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("payment_instructions", sa.String(length=2000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_commission_payment_settings_id"),
        "commission_payment_settings",
        ["id"],
        unique=False,
    )

    op.create_index(
        "uq_commission_payment_settings_active_currency",
        "commission_payment_settings",
        ["currency"],
        unique=True,
        postgresql_where=sa.text("is_active IS true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_commission_payment_settings_active_currency",
        table_name="commission_payment_settings",
    )
    op.drop_index(
        op.f("ix_commission_payment_settings_id"),
        table_name="commission_payment_settings",
    )
    op.drop_table("commission_payment_settings")
