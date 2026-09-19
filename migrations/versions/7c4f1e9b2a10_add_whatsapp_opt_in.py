"""add whatsapp opt in

Revision ID: 7c4f1e9b2a10
Revises: 16e79180eb65
"""

from alembic import op
import sqlalchemy as sa


revision = "7c4f1e9b2a10"
down_revision = "16e79180eb65"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "whatsapp_opt_in",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "whatsapp_opt_in_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.alter_column("users", "whatsapp_opt_in", server_default=None)


def downgrade():
    op.drop_column("users", "whatsapp_opt_in_at")
    op.drop_column("users", "whatsapp_opt_in")
