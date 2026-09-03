import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from sqlalchemy.orm import relationship
from app.db.session import Base


class ListingStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    ARCHIVED = "ARCHIVED"


class ListingType(str, enum.Enum):
    ASSET = "ASSET"
    EQUIPMENT = "EQUIPMENT"
    SERVICE = "SERVICE"
    OPPORTUNITY = "OPPORTUNITY"


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)

    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    category_id = Column(
        Integer,
        ForeignKey("listing_categories.category_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    listing_type = Column(
        SQLEnum(ListingType),
        nullable=False,
        default=ListingType.ASSET,
        index=True,
    )

    price = Column(Float, nullable=True)
    currency = Column(String(3), nullable=False, default="USD")

    is_negotiable = Column(Boolean, nullable=False, default=True)

    status = Column(
        SQLEnum(ListingStatus),
        nullable=False,
        default=ListingStatus.DRAFT,
        index=True,
    )

    version = Column(Integer, nullable=False, default=1)

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

    owner = relationship(
        "UserModel",
        back_populates="listings",
        foreign_keys=[owner_id],
    )

    category = relationship(
        "ListingCategory",
        back_populates="listings",
        foreign_keys=[category_id],
    )

    locations = relationship(
        "ListingLocation",
        back_populates="listing",
        cascade="all, delete-orphan",
    )

    specs = relationship(
        "ListingSpec",
        back_populates="listing",
        cascade="all, delete-orphan",
    )

    media = relationship(
        "ListingMedia",
        back_populates="listing",
        cascade="all, delete-orphan",
    )

    offers = relationship(
        "Offer",
        back_populates="listing",
    )


Index(
    "ix_listings_owner_status",
    Listing.owner_id,
    Listing.status,
)

Index(
    "ix_listings_category_status",
    Listing.category_id,
    Listing.status,
)
