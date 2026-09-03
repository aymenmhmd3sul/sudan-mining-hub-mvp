from sqlalchemy import Column, ForeignKey, Integer, String, Index
from sqlalchemy.orm import relationship

from app.db.session import Base


class ListingLocation(Base):
    __tablename__ = "listing_locations"

    id = Column(Integer, primary_key=True, index=True)

    listing_id = Column(
        Integer,
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    country = Column(String(100), nullable=True)
    state_province = Column(String(150), nullable=True)
    locality = Column(String(150), nullable=True)
    address = Column(String(255), nullable=True)

    latitude = Column(String(32), nullable=True)
    longitude = Column(String(32), nullable=True)

    listing = relationship(
        "Listing",
        back_populates="locations",
    )


Index(
    "ix_listing_locations_region",
    ListingLocation.country,
    ListingLocation.state_province,
    ListingLocation.locality,
)
