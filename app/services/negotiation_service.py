from sqlalchemy.orm import Session

from app.models.negotiation import (
    NegotiationMessage,
    NegotiationParticipant,
    NegotiationRoom,
    NegotiationStatus,
)
from app.models.offer import Offer, OfferStatus
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone

from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.deal import Deal
from app.services.deal_service import DealService
from app.services.commission_service import CommissionService


class NegotiationService:
    @staticmethod
    def get_room(db: Session, room_id: int) -> NegotiationRoom | None:
        return (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.id == room_id)
            .first()
        )

    @staticmethod
    def list_rooms_for_request(
        db: Session,
        request_id: int,
        limit: int = 100,
    ) -> list[NegotiationRoom]:
        return (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.request_id == request_id)
            .order_by(NegotiationRoom.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def create_room(db: Session, **data) -> NegotiationRoom:
        room = NegotiationRoom(**data)
        db.add(room)
        db.commit()
        db.refresh(room)
        return room

    @staticmethod
    def add_participant(
        db: Session,
        room_id: int,
        user_id: int,
    ) -> NegotiationParticipant:
        participant = NegotiationParticipant(
            room_id=room_id,
            user_id=user_id,
        )
        db.add(participant)
        db.commit()
        db.refresh(participant)
        return participant

    @staticmethod
    def approve_negotiation(
        db: Session,
        room_id: int,
        merchant_id: int,
    ) -> NegotiationRoom:
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

        request = (
            db.query(BuyerRequest)
            .filter(BuyerRequest.id == room.request_id)
            .first()
        )

        if request is None:
            raise ValueError("Buyer request not found")

        if request.listing_id is None:
            raise ValueError(
                "Buyer request must be linked to a listing"
            )

        from app.models.listing import Listing, ListingStatus

        listing = (
            db.query(Listing)
            .filter(Listing.id == request.listing_id)
            .first()
        )

        if listing is None:
            raise ValueError("Listing not found")

        from app.services.listing_service import ListingService

        ListingService.require_quantity_classified(listing)

        if listing.status != ListingStatus.ACTIVE:
            raise ValueError("Listing is no longer available")

        if listing.owner_id != merchant_id:
            raise PermissionError(
                "Only the listing merchant can approve this negotiation"
            )

        participant = (
            db.query(NegotiationParticipant)
            .filter(
                NegotiationParticipant.room_id == room.id,
                NegotiationParticipant.user_id == merchant_id,
            )
            .first()
        )

        if participant is None:
            raise PermissionError(
                "Merchant is not a participant in this negotiation room"
            )

        if room.merchant_approved_at is None:
            room.merchant_approved_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(room)
        return room

    @staticmethod
    def finalize_offer(
        db: Session,
        offer_id: int,
        merchant_id: int,
    ) -> NegotiationRoom:
        from app.models.listing import Listing, ListingStatus

        offer = (
            db.query(Offer)
            .filter(Offer.id == offer_id)
            .with_for_update()
            .first()
        )
        if offer is None:
            raise ValueError("Offer not found")

        request = (
            db.query(BuyerRequest)
            .filter(BuyerRequest.id == offer.request_id)
            .first()
        )
        if request is None:
            raise ValueError("Buyer request not found")

        # Every new negotiation/final offer must be isolated to one listing.
        # Legacy offers with no listing remain untouched, but cannot enter
        # the new final-sale flow.
        if offer.listing_id is None:
            raise ValueError("Offer must be linked to a listing before finalization")

        if request.listing_id is None:
            raise ValueError("Buyer request must be linked to a listing before finalization")

        if offer.listing_id != request.listing_id:
            raise ValueError("Offer is not linked to the requested listing")

        if offer.merchant_id != merchant_id:
            raise PermissionError(
                "Only the offer merchant can finalize this offer"
            )

        if offer.status != OfferStatus.SUBMITTED:
            raise ValueError("Only submitted offers can be finalized")

        room = (
            db.query(NegotiationRoom)
            .filter(
                NegotiationRoom.offer_id == offer.id,
                NegotiationRoom.request_id == request.id,
            )
            .order_by(NegotiationRoom.id.desc())
            .first()
        )
        if room is None:
            raise ValueError("Negotiation room for this offer not found")

        if room.status != NegotiationStatus.OPEN:
            raise ValueError("Negotiation room is not open")

        if room.merchant_approved_at is None:
            raise ValueError(
                "Merchant must approve the negotiation before approving the offer"
            )

        participant = (
            db.query(NegotiationParticipant)
            .filter(
                NegotiationParticipant.room_id == room.id,
                NegotiationParticipant.user_id == merchant_id,
            )
            .first()
        )
        if participant is None:
            raise PermissionError(
                "Merchant is not a participant in this negotiation room"
            )

        listing = None
        if offer.listing_id is not None:
            listing = (
                db.query(Listing)
                .filter(Listing.id == offer.listing_id)
                .with_for_update()
                .first()
            )
        if listing is None:
            raise ValueError("Listing not found")

        from app.services.listing_service import ListingService

        ListingService.require_quantity_classified(listing)

        if listing.status != ListingStatus.ACTIVE:
            raise ValueError("Listing is no longer available")

        if offer.listing_id != request.listing_id:
            raise ValueError(
                "Offer is not linked to the requested listing"
            )

        if listing.owner_id != merchant_id:
            raise PermissionError(
                "Merchant does not own the requested listing"
            )

        try:
            final_amount = Decimal(str(offer.amount))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError("Offer amount must be a valid decimal amount")

        if final_amount <= 0:
            raise ValueError("Offer amount must be greater than zero")

        # Prevent two final deals from being opened for the same listing.
        if listing is not None:
            existing_final = (
                db.query(Offer)
                .filter(
                    Offer.listing_id == listing.id,
                    Offer.id != offer.id,
                    Offer.status == OfferStatus.FINAL,
                )
                .first()
            )
            if existing_final is not None:
                raise ValueError(
                    "Another final offer is already awaiting buyer approval"
                )

            from app.models.deal import Deal, DealStatus

            existing_pending_deal = (
                db.query(Deal)
                .filter(
                    Deal.listing_id == listing.id,
                    Deal.status == DealStatus.PENDING_BUYER_APPROVAL,
                    Deal.offer_id != offer.id,
                )
                .first()
            )
            if existing_pending_deal is not None:
                raise ValueError(
                    "Another deal is already awaiting buyer approval"
                )

        currency = offer.currency or request.currency or "SDG"

        try:
            deal = DealService.create(
                db,
                request_id=request.id,
                offer_id=offer.id,
                listing_id=offer.listing_id,
                negotiation_room_id=room.id,
                buyer_id=request.buyer_id,
                merchant_id=offer.merchant_id,
                final_amount=final_amount,
                currency=currency,
                commit=False,
            )

            from app.services.commission_tier_service import CommissionTierService

            tier = CommissionTierService.get_for_amount(
                db,
                currency,
                final_amount,
            )

            if tier is not None:
                final_commission, adjusted_by_platform = (
                    CommissionService.calculate_platform_commission(
                        deal_amount=final_amount,
                        merchant_amount=None,
                        merchant_rate=None,
                        minimum_amount=tier.minimum_amount,
                        platform_rate=tier.commission_rate,
                        currency=currency,
                    )
                )
                platform_amount = (
                    final_amount
                    * tier.commission_rate
                    / Decimal("100")
                )

                CommissionService.create(
                    db,
                    deal_id=deal.id,
                    merchant_id=offer.merchant_id,
                    proposed_amount=None,
                    proposed_currency=None,
                    proposed_rate=None,
                    platform_amount=platform_amount,
                    platform_rate=tier.commission_rate,
                    minimum_amount=tier.minimum_amount,
                    final_amount=final_commission,
                    currency=currency,
                    adjusted_by_platform=adjusted_by_platform,
                )
            else:
                settings = CommissionService.get_active_settings(
                    db,
                    currency,
                )

                final_commission, adjusted_by_platform = (
                    CommissionService.calculate_platform_commission(
                        deal_amount=final_amount,
                        merchant_amount=None,
                        merchant_rate=None,
                        minimum_amount=settings.minimum_amount,
                        platform_rate=settings.commission_rate,
                        currency=currency,
                    )
                )
                platform_amount = (
                    final_amount
                    * settings.commission_rate
                    / Decimal("100")
                )

                CommissionService.create(
                    db,
                    deal_id=deal.id,
                    merchant_id=offer.merchant_id,
                    proposed_amount=None,
                    proposed_currency=None,
                    proposed_rate=None,
                    platform_amount=platform_amount,
                    platform_rate=settings.commission_rate,
                    minimum_amount=settings.minimum_amount,
                    final_amount=final_commission,
                    currency=currency,
                    adjusted_by_platform=adjusted_by_platform,
                )

            offer.status = OfferStatus.FINAL
            room.status = NegotiationStatus.AGREED
            request.status = RequestStatus.NEGOTIATING

            db.commit()
            db.refresh(room)
            return room

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def accept_offer(
        db: Session,
        offer_id: int,
        buyer_id: int,
    ) -> NegotiationRoom:
        offer = (
            db.query(Offer)
            .filter(Offer.id == offer_id)
            .first()
        )
        if offer is None:
            raise ValueError("Offer not found")

        request = (
            db.query(BuyerRequest)
            .filter(BuyerRequest.id == offer.request_id)
            .first()
        )
        if request is None:
            raise ValueError("Buyer request not found")

        if request.buyer_id != buyer_id:
            raise PermissionError("Only the request owner can accept an offer")

        room = (
            db.query(NegotiationRoom)
            .filter(
                NegotiationRoom.offer_id == offer.id,
                NegotiationRoom.request_id == request.id,
            )
            .order_by(NegotiationRoom.id.desc())
            .first()
        )
        if room is None:
            raise ValueError("Negotiation room for this offer not found")

        participant = (
            db.query(NegotiationParticipant)
            .filter(
                NegotiationParticipant.room_id == room.id,
                NegotiationParticipant.user_id == buyer_id,
            )
            .first()
        )
        if participant is None:
            raise PermissionError(
                "Buyer is not a participant in this negotiation room"
            )

        from app.models.deal import Deal, DealStatus

        deal = (
            db.query(Deal)
            .filter(Deal.offer_id == offer.id)
            .first()
        )
        if deal is None:
            raise ValueError("Deal for this final offer not found")

        repeated_approval = (
            deal.status == DealStatus.CONFIRMED and deal.buyer_approved
        )
        if not repeated_approval:
            if offer.status != OfferStatus.FINAL:
                raise ValueError(
                    "Only final offers can be accepted by the buyer"
                )
            if room.status != NegotiationStatus.AGREED:
                raise ValueError(
                    "This final offer is not awaiting buyer approval"
                )

        try:
            DealService.approve_by_buyer(
                db,
                deal=deal,
                buyer_id=buyer_id,
                commit=False,
            )
            if not repeated_approval:
                db.commit()
            db.refresh(room)
            return room

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def add_message(
        db: Session,
        room_id: int,
        sender_id: int,
        body: str,
    ) -> NegotiationMessage:
        message = NegotiationMessage(
            room_id=room_id,
            sender_id=sender_id,
            body=body,
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
