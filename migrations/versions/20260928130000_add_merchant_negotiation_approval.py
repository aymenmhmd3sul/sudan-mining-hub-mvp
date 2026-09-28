"""add merchant negotiation approval timestamp

Revision ID: add_merchant_negotiation_approval_20260928
Revises: add_final_offerstatus_20260928
Create Date: 2026-09-28
"""

from alembic import op
import sqlalchemy as sa


revision = "merchant_approval_20260928"
down_revision = "add_final_offerstatus_20260928"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "negotiation_rooms",
        sa.Column(
            "merchant_approved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "negotiation_rooms",
        "merchant_approved_at",
    )
