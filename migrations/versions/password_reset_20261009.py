"""Add password reset fields and authentication token version.

Revision ID: password_reset_20261009
Revises: 20261002100000
Create Date: 2026-10-09
"""

from alembic import op
import sqlalchemy as sa


revision = "password_reset_20261009"
down_revision = "20261002100000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_reset_token_hash", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_reset_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_reset_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_reset_requested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "auth_token_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "auth_token_version")
    op.drop_column("users", "password_reset_requested_at")
    op.drop_column("users", "password_reset_attempts")
    op.drop_column("users", "password_reset_expires_at")
    op.drop_column("users", "password_reset_token_hash")
