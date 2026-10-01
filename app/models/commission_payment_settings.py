from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String
from sqlalchemy.sql import func

from app.db.session import Base


class CommissionPaymentSettings(Base):
    __tablename__ = "commission_payment_settings"

    id = Column(Integer, primary_key=True, index=True)

    currency = Column(
        String(3),
        nullable=False,
    )

    account_number = Column(
        String(255),
        nullable=True,
    )

    account_name = Column(
        String(255),
        nullable=True,
    )

    payment_instructions = Column(
        String(2000),
        nullable=True,
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
            "uq_commission_payment_settings_active_currency",
            "currency",
            unique=True,
            postgresql_where=(is_active.is_(True)),
        ),
    )
