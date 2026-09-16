from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String, Index
from sqlalchemy.sql import func

from app.db.session import Base


class CommissionTier(Base):
    __tablename__ = "commission_tiers"

    id = Column(Integer, primary_key=True, index=True)

    currency = Column(String(3), nullable=False)

    max_amount = Column(
        Numeric(18, 2),
        nullable=True,
    )

    commission_rate = Column(
        Numeric(8, 4),
        nullable=False,
    )

    minimum_amount = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

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
            "ix_commission_tiers_currency_active",
            "currency",
            "is_active",
        ),
    )
