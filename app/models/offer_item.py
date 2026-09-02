from sqlalchemy import Column, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship

from app.db.session import Base


class OfferItem(Base):
    __tablename__ = "offer_items"

    id = Column(Integer, primary_key=True, index=True)

    offer_id = Column(
        Integer,
        ForeignKey("offers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    request_item_id = Column(
        Integer,
        ForeignKey("request_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    listing_id = Column(
        Integer,
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    quantity = Column(
        Integer,
        nullable=False,
    )

    unit_price = Column(
        Numeric(18, 2),
        nullable=False,
    )

    total_price = Column(
        Numeric(18, 2),
        nullable=False,
    )

    offer = relationship("Offer", back_populates="items")
    request_item = relationship("RequestItem")
    listing = relationship("Listing")
