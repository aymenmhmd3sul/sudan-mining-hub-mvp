from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.offer import Offer, OfferStatus
from app.models.offer_item import OfferItem
from app.models.request_item import RequestItem
from app.models.buyer_request import BuyerRequest
from app.models.listing import Listing, ListingStatus
from app.models.negotiation import (
    NegotiationParticipant,
    NegotiationRoom,
    NegotiationStatus,
)


class OfferService:
    @staticmethod
    def get_by_id(db: Session, offer_id: int) -> Offer | None:
        return (
            db.query(Offer)
            .filter(Offer.id == offer_id)
            .first()
        )

    @staticmethod
    def list_for_request(
        db: Session,
        request_id: int,
        limit: int = 100,
    ) -> list[Offer]:
        return (
            db.query(Offer)
            .filter(Offer.request_id == request_id)
            .order_by(Offer.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(
        db: Session,
        *,
        items: list[dict] | None = None,
        commit: bool = True,
        **data,
    ) -> Offer:
        items = items or []

        if not items:
            raise ValueError("Offer must contain at least one item")

        request_id = data.get("request_id")
        if request_id is None:
            raise ValueError("request_id is required")

        request = (
            db.query(BuyerRequest)
            .filter(BuyerRequest.id == request_id)
            .first()
        )
        if request is None:
            raise ValueError("Buyer request not found")

        if request.listing_id is not None:
            listing = (
                db.query(Listing)
                .filter(Listing.id == request.listing_id)
                .first()
            )
            if listing is None:
                raise ValueError("Listing not found")

            if listing.status != ListingStatus.ACTIVE:
                raise ValueError("Listing is no longer available")

            merchant_id = data.get("merchant_id")
            if merchant_id != listing.owner_id:
                raise ValueError("Merchant can only offer on their own listing")

            for item in items:
                item_listing_id = item.get("listing_id")
                if item_listing_id != request.listing_id:
                    raise ValueError(
                        "Every OfferItem must reference the requested listing"
                    )

        request_item_ids = [int(item["request_item_id"]) for item in items]
        request_items = (
            db.query(RequestItem)
            .filter(
                RequestItem.id.in_(request_item_ids),
                RequestItem.request_id == request_id,
            )
            .all()
        )
        request_items_by_id = {item.id: item for item in request_items}

        if len(request_items_by_id) != len(set(request_item_ids)):
            raise ValueError(
                "Every OfferItem must reference a RequestItem belonging to the request"
            )

        offer_items = []
        grand_total = Decimal("0.00")

        try:
            for payload in items:
                quantity = int(payload["quantity"])
                unit_price = Decimal(str(payload["unit_price"]))

                if quantity <= 0:
                    raise ValueError("OfferItem quantity must be greater than zero")
                if unit_price < 0:
                    raise ValueError("OfferItem unit_price cannot be negative")

                total_price = (
                    unit_price * Decimal(quantity)
                ).quantize(Decimal("0.01"))

                offer_items.append(
                    OfferItem(
                        request_item_id=int(payload["request_item_id"]),
                        listing_id=payload.get("listing_id"),
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price,
                    )
                )
                grand_total += total_price

        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise ValueError(f"Invalid OfferItem payload: {exc}") from exc

        data["amount"] = str(grand_total.quantize(Decimal("0.01")))
        if request.listing_id is not None:
            data["listing_id"] = request.listing_id

        offer = Offer(**data)
        offer.items = offer_items

        db.add(offer)

        if commit:
            try:
                db.commit()
                db.refresh(offer)
            except Exception:
                db.rollback()
                raise
        else:
            db.flush()

        return offer

    @staticmethod
    def create_buyer_offer(
        db: Session,
        *,
        room_id: int,
        buyer_id: int,
        currency: str | None = None,
        message: str | None = None,
        items: list[dict] | None = None,
    ) -> tuple[Offer, NegotiationRoom]:
        room = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.id == room_id)
            .with_for_update()
            .first()
        )
        if room is None:
            raise ValueError("Negotiation room not found")

        if room.status != NegotiationStatus.OPEN:
            raise ValueError("Negotiation room is not open")

        if room.merchant_approved_at is None:
            raise ValueError("Merchant approval is required before submitting an offer")

        request = (
            db.query(BuyerRequest)
            .filter(BuyerRequest.id == room.request_id)
            .first()
        )
        if request is None:
            raise ValueError("Buyer request not found")

        if request.buyer_id != buyer_id:
            raise PermissionError("Only the buyer who started the request can submit an offer")

        participant = (
            db.query(NegotiationParticipant)
            .filter(
                NegotiationParticipant.room_id == room.id,
                NegotiationParticipant.user_id == buyer_id,
            )
            .first()
        )
        if participant is None:
            raise PermissionError("Buyer is not a participant in this negotiation")

        listing = None
        if request.listing_id is not None:
            listing = (
                db.query(Listing)
                .filter(Listing.id == request.listing_id)
                .first()
            )
            if listing is None:
                raise ValueError("Listing not found")

            if listing.status != ListingStatus.ACTIVE:
                raise ValueError("Listing is no longer available")

        if room.offer_id is not None:
            raise ValueError("An offer has already been submitted for this negotiation")

        if listing is None:
            raise ValueError("A listing is required for this negotiation")

        offer = OfferService.create(
            db,
            request_id=request.id,
            merchant_id=listing.owner_id,
            currency=currency or request.currency,
            message=message,
            status=OfferStatus.SUBMITTED,
            items=items,
            commit=False,
        )

        room.offer_id = offer.id
        db.flush()

        return offer, room
