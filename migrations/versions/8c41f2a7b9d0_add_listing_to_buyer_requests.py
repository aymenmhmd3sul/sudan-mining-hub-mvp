"""add listing reference to buyer requests

Revision ID: 8c41f2a7b9d0
Revises: 34dce851e32a
Create Date: 2026-09-03
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8c41f2a7b9d0"
down_revision: Union[str, Sequence[str], None] = "34dce851e32a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "buyer_requests",
        sa.Column("listing_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_buyer_requests_listing_id",
        "buyer_requests",
        ["listing_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_buyer_requests_listing_id_listings",
        "buyer_requests",
        "listings",
        ["listing_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_buyer_requests_listing_id_listings",
        "buyer_requests",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_buyer_requests_listing_id",
        table_name="buyer_requests",
    )
    op.drop_column("buyer_requests", "listing_id")
