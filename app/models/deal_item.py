from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.db.session import Base


class DealItem(Base):
    __tablename__ = "deal_items"

    id = Column(Integer, primary_key=True, index=True)

    deal_id = Column(
        Integer,
        ForeignKey("deals.id", ondelete="CASCADE"),
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

    title = Column(
        String(255),
        nullable=False,
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

    deal = relationship("Deal", back_populates="items")
    request_item = relationship("RequestItem")
    listing = relationship("Listing")
