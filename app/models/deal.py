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


class DealStatus(str, enum.Enum):
    PENDING_BUYER_APPROVAL = "PENDING_BUYER_APPROVAL"
    CONFIRMED = "CONFIRMED"
    DELIVERED = "DELIVERED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)

    request_id = Column(
        Integer,
        ForeignKey("buyer_requests.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    offer_id = Column(
        Integer,
        ForeignKey("offers.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )

    listing_id = Column(
        Integer,
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    negotiation_room_id = Column(
        Integer,
        ForeignKey("negotiation_rooms.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    buyer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    merchant_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
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

    status = Column(
        SQLEnum(DealStatus),
        nullable=False,
        default=DealStatus.PENDING_BUYER_APPROVAL,
        index=True,
    )

    buyer_approved = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    approved_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    delivered_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    received_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    ownership_transfer_reference = Column(
        String(255),
        nullable=True,
    )

    negotiation_evidence_hash = Column(
        String(64),
        nullable=True,
        unique=True,
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

    request = relationship(
        "BuyerRequest",
        foreign_keys=[request_id],
    )

    offer = relationship(
        "Offer",
        foreign_keys=[offer_id],
    )

    listing = relationship(
        "Listing",
        foreign_keys=[listing_id],
    )

    negotiation_room = relationship(
        "NegotiationRoom",
        foreign_keys=[negotiation_room_id],
    )

    buyer = relationship(
        "UserModel",
        foreign_keys=[buyer_id],
    )

    merchant = relationship(
        "UserModel",
        foreign_keys=[merchant_id],
    )

    items = relationship(
        "DealItem",
        back_populates="deal",
        cascade="all, delete-orphan",
    )

    commission = relationship(
        "Commission",
        back_populates="deal",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_deals_buyer_status",
            buyer_id,
            status,
        ),
        Index(
            "ix_deals_merchant_status",
            merchant_id,
            status,
        ),
        Index(
            "ix_deals_request_status",
            request_id,
            status,
        ),
    )
