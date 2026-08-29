from sqlalchemy import Column, Integer, String, ForeignKey


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
