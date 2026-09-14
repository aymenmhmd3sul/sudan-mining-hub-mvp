"""add subscription pricing and payments

Revision ID: c8f21a6d4e91
Revises: 7d4a91f0e3c2
"""

from alembic import op
import sqlalchemy as sa


revision = "c8f21a6d4e91"
down_revision = "7d4a91f0e3c2"
branch_labels = None
depends_on = None


subscription_payment_status = sa.Enum(
    "PENDING",
    "PAID",
    "FAILED",
    "REFUNDED",
    "CANCELLED",
    name="subscriptionpaymentstatus",
)


def upgrade():
    op.create_table(
        "subscription_pricing",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column(
            "billing_period_months",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_subscription_pricing_id",
        "subscription_pricing",
        ["id"],
        unique=False,
    )

    op.create_index(
        "uq_subscription_pricing_active_plan_currency",
        "subscription_pricing",
        ["plan", "currency"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )

    op.create_table(
        "subscription_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            sa.Integer(),
            sa.ForeignKey("subscriptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("plan", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "status",
            subscription_payment_status,
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("payment_method", sa.String(length=50), nullable=True),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column(
            "external_reference",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "paid_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_subscription_payments_id",
        "subscription_payments",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_payments_user_id",
        "subscription_payments",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_payments_subscription_id",
        "subscription_payments",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_payments_status",
        "subscription_payments",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_payments_external_reference",
        "subscription_payments",
        ["external_reference"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_payments_provider_external_reference",
        "subscription_payments",
        ["provider", "external_reference"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_subscription_payments_provider_external_reference",
        table_name="subscription_payments",
    )
    op.drop_index(
        "ix_subscription_payments_external_reference",
        table_name="subscription_payments",
    )
    op.drop_index(
        "ix_subscription_payments_status",
        table_name="subscription_payments",
    )
    op.drop_index(
        "ix_subscription_payments_subscription_id",
        table_name="subscription_payments",
    )
    op.drop_index(
        "ix_subscription_payments_user_id",
        table_name="subscription_payments",
    )
    op.drop_index(
        "ix_subscription_payments_id",
        table_name="subscription_payments",
    )
    op.drop_table("subscription_payments")

    subscription_payment_status.drop(op.get_bind())

    op.drop_index(
        "uq_subscription_pricing_active_plan_currency",
        table_name="subscription_pricing",
    )
    op.drop_index(
        "ix_subscription_pricing_id",
        table_name="subscription_pricing",
    )
    op.drop_table("subscription_pricing")
