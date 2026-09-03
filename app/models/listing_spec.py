from sqlalchemy import Column, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import relationship

from app.db.session import Base


class ListingSpec(Base):
    __tablename__ = "listing_specs"

    id = Column(Integer, primary_key=True, index=True)

    listing_id = Column(
        Integer,
        ForeignKey("listings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    spec_key = Column(String(100), nullable=False)
    spec_value = Column(Text, nullable=True)
    unit = Column(String(50), nullable=True)

    listing = relationship(
        "Listing",
        back_populates="specs",
    )


Index(
    "ix_listing_specs_listing_key",
    ListingSpec.listing_id,
    ListingSpec.spec_key,
)
