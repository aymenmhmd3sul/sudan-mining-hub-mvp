"""add DELIVERED to dealstatus enum

Revision ID: b7d4e91c2a6f
Revises: 93ec6a97adeb
Create Date: 2026-09-04
"""

from alembic import op


revision = "b7d4e91c2a6f"
down_revision = "93ec6a97adeb"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TYPE dealstatus ADD VALUE IF NOT EXISTS 'DELIVERED'"
    )


def downgrade():
    raise RuntimeError(
        "PostgreSQL enum value DELIVERED cannot be safely removed automatically"
    )
