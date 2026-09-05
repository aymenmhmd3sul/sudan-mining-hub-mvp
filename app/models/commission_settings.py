from sqlalchemy import Boolean, Column, DateTime, Index, Integer, Numeric, String
from sqlalchemy.sql import func

from app.db.session import Base


class CommissionSettings(Base):
    __tablename__ = "commission_settings"

    id = Column(Integer, primary_key=True, index=True)

    currency = Column(
        String(3),
        nullable=False,
    )

    commission_rate = Column(
        Numeric(8, 4),
        nullable=False,
    )

    minimum_amount = Column(
        Numeric(18, 2),
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
            "uq_commission_settings_active_currency",
            "currency",
            unique=True,
            postgresql_where=(is_active.is_(True)),
        ),
    )
