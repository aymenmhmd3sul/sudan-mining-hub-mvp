"""seed active SDG commission settings

Revision ID: 43189b528483
Revises: a75902c7237c
Create Date: 2026-09-05 16:48:45.341556

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '43189b528483'
down_revision: Union[str, Sequence[str], None] = 'a75902c7237c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO commission_settings
                (currency, commission_rate, minimum_amount, is_active)
            VALUES
                ('SDG', 3.0000, 1000.00, TRUE)
            """
        )
    )


def downgrade() -> None:    op.execute(
        sa.text(
            """
            DELETE FROM commission_settings
            WHERE currency = 'SDG'
              AND commission_rate = 3.0000
              AND minimum_amount = 1000.00
              AND is_active = TRUE
            """
        )
    )
