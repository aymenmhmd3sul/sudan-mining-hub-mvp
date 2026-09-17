"""align subscription status with ORM enum

Revision ID: d16f79_subscription_status_enum
Revises: commission_tiers_progressive
"""

from alembic import op
import sqlalchemy as sa


revision = "d16f79_subscription_status_enum"
down_revision = "commission_tiers_progressive"
branch_labels = None
depends_on = None


SUBSCRIPTION_STATUS_VALUES = (
    "PENDING",
    "ACTIVE",
    "EXPIRED",
    "CANCELLED",
    "SUSPENDED",
)


def upgrade():
    enum_values = ", ".join(
        "'" + value.replace("'", "''") + "'"
        for value in SUBSCRIPTION_STATUS_VALUES
    )

    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'subscriptionstatus'
            ) THEN
                CREATE TYPE subscriptionstatus AS ENUM ({enum_values});
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        ALTER TABLE subscriptions
        ALTER COLUMN status TYPE subscriptionstatus
        USING status::text::subscriptionstatus
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE subscriptions
        ALTER COLUMN status TYPE VARCHAR(20)
        USING status::text
        """
    )

    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
