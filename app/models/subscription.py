import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class SubscriptionStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    SUSPENDED = "SUSPENDED"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    plan = Column(String(100), nullable=False)
    status = Column(
        Enum(SubscriptionStatus),
        nullable=False,
        default=SubscriptionStatus.PENDING,
        index=True,
    )

    started_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    renewal_reference = Column(String(255), nullable=True)
    payment_reference = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    user = relationship("UserModel", back_populates="subscriptions")
