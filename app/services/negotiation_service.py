from sqlalchemy.orm import Session

from app.models.negotiation import (
    NegotiationMessage,
    NegotiationParticipant,
    NegotiationRoom,
    NegotiationStatus,
)
from app.models.offer import Offer, OfferStatus
from decimal import Decimal, InvalidOperation

from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.deal import Deal
from app.services.deal_service import DealService


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

        if offer.status != OfferStatus.SUBMITTED:
            raise ValueError("Only submitted offers can be accepted")

        if request.status not in (
            RequestStatus.OPEN,
            RequestStatus.NEGOTIATING,
        ):
            raise ValueError("Buyer request is not open for negotiation")

        room = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.offer_id == offer.id)
            .first()
        )
        if room is None:
            raise ValueError("Negotiation room not found")

        offer.status = OfferStatus.ACCEPTED
        room.status = NegotiationStatus.AGREED
        request.status = RequestStatus.NEGOTIATING

        competing_offers = (
            db.query(Offer)
            .filter(
                Offer.request_id == request.id,
                Offer.id != offer.id,
                Offer.status == OfferStatus.SUBMITTED,
            )
            .all()
        )

        for competing_offer in competing_offers:
            competing_offer.status = OfferStatus.REJECTED

            competing_room = (
                db.query(NegotiationRoom)
                .filter(NegotiationRoom.offer_id == competing_offer.id)
                .first()
            )
            if competing_room is not None:
                competing_room.status = NegotiationStatus.CLOSED

        existing_deal = (
            db.query(Deal)
            .filter(Deal.offer_id == offer.id)
            .first()
        )

        if existing_deal is None:
            try:
                final_amount = Decimal(str(offer.amount))
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError("Offer amount must be a valid decimal amount")

            DealService.create(
                db,
                request_id=request.id,
                offer_id=offer.id,
                listing_id=offer.listing_id,
                negotiation_room_id=room.id,
                buyer_id=request.buyer_id,
                merchant_id=offer.merchant_id,
                final_amount=final_amount,
                currency=offer.currency or request.currency or "SDG",
            )

        db.commit()
        db.refresh(room)
        return room

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
