"""add subscriptions

Revision ID: 482b90e7ab23
Revises: b78a05f8e132
Create Date: 2026-09-11 06:09:59.349132

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '482b90e7ab23'
down_revision: Union[str, Sequence[str], None] = 'b78a05f8e132'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
