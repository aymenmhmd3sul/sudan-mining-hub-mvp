from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


from app.db.session import Base


class ListingCategory(Base):
    __tablename__ = "listing_categories"

    category_id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False, index=True)

    status = Column(String, nullable=False, default="ACTIVE")

    parent_category_id = Column(
        Integer,
        ForeignKey("listing_categories.category_id"),
        nullable=True,
        index=True,
    )

    description = Column(String, nullable=True)

    sort_order = Column(Integer, nullable=True)

    parent = relationship(
        "ListingCategory",
        remote_side=[category_id],
        back_populates="children",
    )

    children = relationship(
        "ListingCategory",
        back_populates="parent",
    )

    listings = relationship(
        "Listing",
        back_populates="category",
    )

    request_items = relationship(
        "RequestItem",
        back_populates="category",
    )
