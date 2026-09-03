import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class CommissionStatus(str, enum.Enum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    PAID = "PAID"


class Commission(Base):
    __tablename__ = "commissions"

    id = Column(Integer, primary_key=True, index=True)

    deal_id = Column(
        Integer,
        ForeignKey("deals.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )

    merchant_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    proposed_amount = Column(
        Numeric(18, 2),
        nullable=True,
    )

    proposed_currency = Column(
        String(3),
        nullable=True,
    )

    proposed_rate = Column(
        Numeric(8, 4),
        nullable=True,
    )

    platform_amount = Column(
        Numeric(18, 2),
        nullable=False,
    )

    platform_rate = Column(
        Numeric(8, 4),
        nullable=True,
    )

    final_amount = Column(
        Numeric(18, 2),
        nullable=False,
    )

    currency = Column(
        String(3),
        nullable=False,
        default="SDG",
    )

    adjusted_by_platform = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    merchant_accepted = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    status = Column(
        SQLEnum(CommissionStatus),
        nullable=False,
        default=CommissionStatus.PENDING,
        index=True,
    )

    claimed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    paid_at = Column(
        DateTime(timezone=True),
        nullable=True,
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

    deal = relationship(
        "Deal",
        back_populates="commission",
        foreign_keys=[deal_id],
    )

    merchant = relationship(
        "UserModel",
        foreign_keys=[merchant_id],
    )

    __table_args__ = (
        Index(
            "ix_commissions_merchant_status",
            merchant_id,
            status,
        ),
    )
