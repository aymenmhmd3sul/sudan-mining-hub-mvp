import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class OfferStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, index=True)

    request_id = Column(
        Integer,
        ForeignKey("buyer_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    merchant_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    listing_id = Column(
        Integer,
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    amount = Column(String(50), nullable=True)
    currency = Column(String(10), nullable=True)

    message = Column(Text, nullable=True)

    status = Column(
        SQLEnum(OfferStatus),
        nullable=False,
        default=OfferStatus.DRAFT,
        index=True,
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
        back_populates="offers",
        foreign_keys="Offer.request_id",
    )

    merchant = relationship(
        "UserModel",
        back_populates="offers",
        foreign_keys="Offer.merchant_id",
    )

    listing = relationship(
        "Listing",
        back_populates="offers",
        foreign_keys="Offer.listing_id",
    )

    items = relationship(
        "OfferItem",
        back_populates="offer",
        cascade="all, delete-orphan",
    )

    negotiation_rooms = relationship(
        "NegotiationRoom",
        back_populates="offer",
        foreign_keys="NegotiationRoom.offer_id",
    )

    __table_args__ = (
        Index(
            "ix_offers_request_status",
            request_id,
            status,
        ),
        Index(
            "ix_offers_merchant_status",
            merchant_id,
            status,
        ),
    )
