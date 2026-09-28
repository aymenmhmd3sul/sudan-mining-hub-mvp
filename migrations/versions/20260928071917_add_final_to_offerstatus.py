"""add FINAL to offerstatus

Revision ID: add_final_offerstatus_20260928
Revises: 7c4f1e9b2a10
Create Date: 2026-09-28
"""

from alembic import op


revision = "add_final_offerstatus_20260928"
down_revision = "7c4f1e9b2a10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE offerstatus ADD VALUE IF NOT EXISTS 'FINAL'"
    )


def downgrade() -> None:
    # PostgreSQL does not safely support removing an enum value
    # that may already exist in stored data.
    pass
