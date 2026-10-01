"""add configurable commission payment settings

Revision ID: commission_payment_settings_20261001
Revises: merchant_approval_20260928
Create Date: 2026-10-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "cps_payment_20261001"
down_revision: Union[str, Sequence[str], None] = "merchant_approval_20260928"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "commission_settings",
        sa.Column(
            "payment_account_number",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "commission_settings",
        sa.Column(
            "payment_account_name",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "commission_settings",
        sa.Column(
            "payment_instructions",
            sa.String(length=2000),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("commission_settings", "payment_instructions")
    op.drop_column("commission_settings", "payment_account_name")
    op.drop_column("commission_settings", "payment_account_number")
