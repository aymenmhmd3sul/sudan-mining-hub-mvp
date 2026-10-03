from sqlalchemy.orm import Session

from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.listing import Listing
from app.services.listing_service import ListingService


class RequestService:
    @staticmethod
    def get_by_id(db: Session, request_id: int) -> BuyerRequest | None:
        return (
            db.query(BuyerRequest)
            .filter(BuyerRequest.id == request_id)
            .first()
        )

    @staticmethod
    def list_open(db: Session, limit: int = 100) -> list[BuyerRequest]:
        return (
            db.query(BuyerRequest)
            .filter(BuyerRequest.status == RequestStatus.OPEN)
            .order_by(BuyerRequest.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def list_for_buyer(
        db: Session,
        buyer_id: int,
        limit: int = 100,
    ) -> list[BuyerRequest]:
        return (
            db.query(BuyerRequest)
            .filter(BuyerRequest.buyer_id == buyer_id)
            .order_by(BuyerRequest.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(db: Session, **data) -> BuyerRequest:
        listing_id = data.get("listing_id")
        if listing_id is not None:
            listing = (
                db.query(Listing)
                .filter(Listing.id == listing_id)
                .first()
            )
            if listing is None:
                raise ValueError("Listing not found")
            ListingService.require_quantity_classified(listing)

        request = BuyerRequest(**data)
        db.add(request)
        db.commit()
        db.refresh(request)
        return request
