"""Store the preferred language for each Web Push subscription."""

from alembic import op
import sqlalchemy as sa

revision: str = "20261027_push_subscription_language"
down_revision: str = "notification_read_state_20261012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "push_subscriptions",
        sa.Column(
            "language",
            sa.String(length=2),
            nullable=False,
            server_default="ar",
        ),
    )


def downgrade() -> None:
    op.drop_column("push_subscriptions", "language")
