"""add progressive commission tiers

Revision ID: commission_tiers_progressive
Revises: c8f21a6d4e91
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "commission_tiers_progressive"
down_revision = "c8f21a6d4e91"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "commission_tiers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("max_amount", sa.Numeric(18, 2), nullable=True),
        sa.Column("commission_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column(
            "minimum_amount",
            sa.Numeric(18, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
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
    )

    op.create_index(
        "ix_commission_tiers_currency_active",
        "commission_tiers",
        ["currency", "is_active"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO commission_tiers
            (currency, max_amount, commission_rate, minimum_amount, is_active)
        VALUES
            ('USD', 1000.00, 0.5000, 0.00, true),
            ('USD', NULL, 1.0000, 0.00, true)
        """
    )


def downgrade():
    op.drop_index(
        "ix_commission_tiers_currency_active",
        table_name="commission_tiers",
    )
    op.drop_table("commission_tiers")
