"""add email verification

Revision ID: 7d4a91f0e3c2
Revises: ffc04725b067
"""

from alembic import op
import sqlalchemy as sa


revision = "7d4a91f0e3c2"
down_revision = "ffc04725b067"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "email_verification_token_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "email_verification_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.alter_column(
        "users",
        "email_verified",
        server_default=sa.false(),
    )


def downgrade():
    op.drop_column("users", "email_verification_expires_at")
    op.drop_column("users", "email_verification_token_hash")
    op.drop_column("users", "email_verified")
