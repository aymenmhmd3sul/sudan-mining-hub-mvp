"""merge commission lifecycle with current deal delivery branch

Revision ID: d16f84
Revises: b7d4e91c2a6f, d16f80
Create Date: 2026-09-05
"""

from alembic import op


revision = "d16f84"
down_revision = ("b7d4e91c2a6f", "d16f80")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade intentionally disabled for financial lifecycle merge"
    )
