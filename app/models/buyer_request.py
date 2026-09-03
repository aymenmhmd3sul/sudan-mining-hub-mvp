import enum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class RequestStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    NEGOTIATING = "NEGOTIATING"
    FULFILLED = "FULFILLED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


class BuyerRequest(Base):
    __tablename__ = "buyer_requests"

    id = Column(Integer, primary_key=True, index=True)

    buyer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(
        SQLEnum(RequestStatus),
        nullable=False,
        default=RequestStatus.DRAFT,
        index=True,
    )

    currency = Column(String(10), nullable=True)
    target_location = Column(String(255), nullable=True)

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

    buyer = relationship(
        "UserModel",
        back_populates="buyer_requests",
        foreign_keys=[buyer_id],
    )

    items = relationship(
        "RequestItem",
        back_populates="request",
        cascade="all, delete-orphan",
    )

    offers = relationship(
        "Offer",
        back_populates="request",
        cascade="all, delete-orphan",
    )

    negotiation_rooms = relationship(
        "NegotiationRoom",
        back_populates="request",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_buyer_requests_buyer_status",
            buyer_id,
            status,
        ),
    )
