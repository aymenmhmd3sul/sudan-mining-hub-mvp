"""add offer items

Revision ID: d9c529a77b16
Revises: 3baa98d42c55
Create Date: 2026-09-01 18:33:55.617514
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9c529a77b16"
down_revision: Union[str, Sequence[str], None] = "3baa98d42c55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "offer_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "offer_id",
            sa.Integer(),
            sa.ForeignKey("offers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "request_item_id",
            sa.Integer(),
            sa.ForeignKey("request_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "listing_id",
            sa.Integer(),
            sa.ForeignKey("listings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(18, 2), nullable=False),
    )

    op.create_index(
        "ix_offer_items_offer_id",
        "offer_items",
        ["offer_id"],
    )
    op.create_index(
        "ix_offer_items_request_item_id",
        "offer_items",
        ["request_item_id"],
    )
    op.create_index(
        "ix_offer_items_listing_id",
        "offer_items",
        ["listing_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_offer_items_listing_id", table_name="offer_items")
    op.drop_index("ix_offer_items_request_item_id", table_name="offer_items")
    op.drop_index("ix_offer_items_offer_id", table_name="offer_items")
    op.drop_table("offer_items")
