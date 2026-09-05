"""reconcile commission lifecycle with domain contract

Revision ID: d16f80
Revises: 3baa98d42c55
Create Date: 2026-09-05
"""

from alembic import op
import sqlalchemy as sa


revision = "d16f80"
down_revision = "3baa98d42c55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "commissions",
        sa.Column("minimum_amount", sa.Numeric(18, 2), nullable=True),
    )

    op.alter_column(
        "commissions",
        "platform_rate",
        existing_type=sa.Numeric(8, 4),
        nullable=False,
    )

    op.add_column(
        "commissions",
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.drop_column("commissions", "claimed_at")
    op.drop_column("commissions", "paid_at")

    op.execute("""
        ALTER TYPE commissionstatus
        RENAME TO commissionstatus_old
    """)

    op.execute("""
        CREATE TYPE commissionstatus AS ENUM (
            'CALCULATED',
            'DUE',
            'SETTLED',
            'WAIVED'
        )
    """)

    op.execute("""
        ALTER TABLE commissions
        ALTER COLUMN status DROP DEFAULT
    """)

    op.execute("""
        ALTER TABLE commissions
        ALTER COLUMN status TYPE commissionstatus
        USING 'CALCULATED'::commissionstatus
    """)

    op.execute("""
        DROP TYPE commissionstatus_old
    """)

    op.execute("""
        ALTER TABLE commissions
        ALTER COLUMN status SET DEFAULT 'CALCULATED'
    """)


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade intentionally disabled for financial lifecycle migration"
    )
