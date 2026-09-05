"""canonical_mvp_baseline

Revision ID: 7350c4ab6e35
Revises: 
Create Date: 2026-08-30 11:51:26.727457

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '7350c4ab6e35'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
