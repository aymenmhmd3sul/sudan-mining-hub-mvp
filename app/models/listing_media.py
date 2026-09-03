import enum

from sqlalchemy import Column, Enum as SQLEnum, ForeignKey, Integer, String, Index
from sqlalchemy.orm import relationship

from app.db.session import Base


class MediaType(str, enum.Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    DOCUMENT = "DOCUMENT"


class ListingMedia(Base):
    __tablename__ = "listing_media"

    id = Column(Integer, primary_key=True, index=True)

    listing_id = Column(
        Integer,
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    media_type = Column(
        SQLEnum(MediaType),
        nullable=False,
        default=MediaType.IMAGE,
    )

    url = Column(String(1000), nullable=False)

    sort_order = Column(Integer, nullable=False, default=0)

    listing = relationship(
        "Listing",
        back_populates="media",
    )


Index(
    "ix_listing_media_listing_order",
    ListingMedia.listing_id,
    ListingMedia.sort_order,
)
