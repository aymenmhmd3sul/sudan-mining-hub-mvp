from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "34dce851e32a"
down_revision: Union[str, Sequence[str], None] = "d9c529a77b16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deal_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "deal_id",
            sa.Integer(),
            sa.ForeignKey("deals.id", ondelete="CASCADE"),
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
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_price", sa.Numeric(18, 2), nullable=False),
    )
    op.create_index("ix_deal_items_deal_id", "deal_items", ["deal_id"])
    op.create_index("ix_deal_items_request_item_id", "deal_items", ["request_item_id"])
    op.create_index("ix_deal_items_listing_id", "deal_items", ["listing_id"])


def downgrade() -> None:
    op.drop_index("ix_deal_items_listing_id", table_name="deal_items")
    op.drop_index("ix_deal_items_request_item_id", table_name="deal_items")
    op.drop_index("ix_deal_items_deal_id", table_name="deal_items")
    op.drop_table("deal_items")
