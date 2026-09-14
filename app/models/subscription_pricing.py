from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, Numeric, String
from sqlalchemy.sql import func

from app.db.session import Base


class SubscriptionPricing(Base):
    __tablename__ = "subscription_pricing"

    id = Column(Integer, primary_key=True, index=True)

    plan = Column(String(100), nullable=False)
    currency = Column(String(3), nullable=False)
    amount = Column(Numeric(18, 2), nullable=False)
    billing_period_months = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "uq_subscription_pricing_active_plan_currency",
            "plan",
            "currency",
            unique=True,
            postgresql_where=(is_active.is_(True)),
        ),
    )

    def validate(self) -> None:
        if not self.plan or not self.plan.strip():
            raise ValueError("Subscription plan is required")
        if len(self.currency or "") != 3:
            raise ValueError("Currency must be a 3-letter code")
        if self.amount is None or Decimal(str(self.amount)) < Decimal("0"):
            raise ValueError("Subscription price cannot be negative")
        if self.billing_period_months < 1:
            raise ValueError("Billing period must be at least one month")
