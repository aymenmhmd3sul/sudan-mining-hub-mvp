from sqlalchemy.orm import Session

from app.models.listing import Listing, ListingStatus


class ListingService:
    @staticmethod
    def get_by_id(db: Session, listing_id: int) -> Listing | None:
        return (
            db.query(Listing)
            .filter(Listing.id == listing_id)
            .first()
        )

    @staticmethod
    def list_active(
        db: Session,
        limit: int = 100,
        search: str | None = None,
        listing_type=None,
        category_id: int | None = None,
    ) -> list[Listing]:
        query = (
            db.query(Listing)
            .filter(Listing.status == ListingStatus.ACTIVE)
        )

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                (Listing.title.ilike(search_term))
                | (Listing.description.ilike(search_term))
            )

        if listing_type is not None:
            query = query.filter(Listing.listing_type == listing_type)

        if category_id is not None:
            query = query.filter(Listing.category_id == category_id)

        return (
            query
            .order_by(Listing.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_pending(
        db: Session,
        limit: int = 100,
    ) -> list[Listing]:
        return (
            db.query(Listing)
            .filter(Listing.status == ListingStatus.DRAFT)
            .order_by(Listing.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def approve(db: Session, listing_id: int) -> Listing:
        listing = (
            db.query(Listing)
            .filter(Listing.id == listing_id)
            .first()
        )

        if listing is None:
            raise ValueError("Listing not found")

        if listing.status != ListingStatus.DRAFT:
            raise ValueError("Only DRAFT listings can be approved")

        listing.status = ListingStatus.ACTIVE
        listing.version += 1

        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def create(db: Session, **data) -> Listing:
        listing = Listing(**data)
        db.add(listing)
        db.commit()
        db.refresh(listing)
        return listing
