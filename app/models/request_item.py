from sqlalchemy import Column, ForeignKey, Integer, String, Text, Index
from sqlalchemy.orm import relationship

from app.db.session import Base


class RequestItem(Base):
    __tablename__ = "request_items"

    id = Column(Integer, primary_key=True, index=True)

    request_id = Column(
        Integer,
        ForeignKey("buyer_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    category_id = Column(
        Integer,
        ForeignKey("listing_categories.category_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    quantity = Column(Integer, nullable=True)
    unit = Column(String(50), nullable=True)

    request = relationship(
        "BuyerRequest",
        back_populates="items",
    )

    category = relationship(
        "ListingCategory",
        back_populates="request_items",
    )

    __table_args__ = (
        Index(
            "ix_request_items_request_category",
            request_id,
            category_id,
        ),
    )
