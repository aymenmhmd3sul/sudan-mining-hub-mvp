"""add optional agent to deals

Revision ID: ffc04725b067
Revises: 19e922331aaa
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ffc04725b067"
down_revision: Union[str, Sequence[str], None] = "19e922331aaa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deals",
        sa.Column(
            "agent_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_deals_agent_id",
        "deals",
        ["agent_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_deals_agent_id_users",
        "deals",
        "users",
        ["agent_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_deals_agent_id_users",
        "deals",
        type_="foreignkey",
    )
    op.drop_index("ix_deals_agent_id", table_name="deals")
    op.drop_column("deals", "agent_id")
