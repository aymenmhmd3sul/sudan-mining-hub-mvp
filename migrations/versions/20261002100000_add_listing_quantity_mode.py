"""Add nullable quantity classification to listings.

Revision ID: 20261002100000
Revises: notif_idem_20261001
Create Date: 2026-10-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20261002100000"
down_revision: Union[str, Sequence[str], None] = "notif_idem_20261001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


quantity_mode_enum = postgresql.ENUM(
    "SINGLE",
    "BULK",
    name="quantitymode",
    schema="public",
    create_type=False,
)


def upgrade() -> None:
    quantity_mode_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "listings",
        sa.Column(
            "quantity_mode",
            quantity_mode_enum,
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("listings", "quantity_mode")
    quantity_mode_enum.drop(op.get_bind(), checkfirst=True)
