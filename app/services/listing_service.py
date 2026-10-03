from sqlalchemy.orm import Session, selectinload

from app.models.listing import Listing, ListingStatus, QuantityMode
from app.models.listing_location import ListingLocation
from app.models.listing_spec import ListingSpec


class ListingService:
    @staticmethod
    def require_quantity_classified(listing: Listing) -> None:
        """Reject listings that have not been explicitly quantity-classified.

        The quantity columns are not part of the current schema yet. Using
        getattr keeps this guard fail-closed until that schema is introduced.
        """
        mode = getattr(listing, "quantity_mode", None)
        mode = getattr(mode, "value", mode)
        if mode not in {"SINGLE", "BULK"}:
            raise ValueError(
                "Listing is not quantity-classified and cannot enter a new sale flow"
            )

    @staticmethod
    def get_by_id(db: Session, listing_id: int) -> Listing | None:
        return (
            db.query(Listing)
            .options(selectinload(Listing.media))
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
            .options(selectinload(Listing.media))
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
    def approve(
        db: Session,
        listing_id: int,
        quantity_mode: QuantityMode | str,
    ) -> Listing:
        listing = (
            db.query(Listing)
            .filter(Listing.id == listing_id)
            .first()
        )

        if listing is None:
            raise ValueError("Listing not found")

        if listing.status != ListingStatus.DRAFT:
            raise ValueError("Only DRAFT listings can be approved")

        mode = getattr(quantity_mode, "value", quantity_mode)
        if mode not in {QuantityMode.SINGLE.value, QuantityMode.BULK.value}:
            raise ValueError("quantity_mode must be SINGLE or BULK")

        listing.quantity_mode = QuantityMode(mode)
        listing.status = ListingStatus.ACTIVE
        listing.version += 1

        db.commit()
        db.refresh(listing)
        return listing

    @staticmethod
    def create(db: Session, **data) -> Listing:
        state_province = data.pop("state_province", None)
        locality = data.pop("locality", None)
        address = data.pop("address", None)
        specs = data.pop("specs", None)

        listing = Listing(**data)
        db.add(listing)
        db.flush()

        if any((state_province, locality, address)):
            db.add(
                ListingLocation(
                    listing_id=listing.id,
                    country="SD",
                    state_province=state_province,
                    locality=locality,
                    address=address,
                )
            )

        if specs and specs.strip():
            db.add(
                ListingSpec(
                    listing_id=listing.id,
                    spec_key="details",
                    spec_value=specs.strip(),
                )
            )

        db.commit()
        db.refresh(listing)
        return listing
