import app.db.base

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.db.session import SessionLocal
from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.deal import Deal, DealStatus
from app.models.negotiation import NegotiationRoom, NegotiationStatus
from app.models.offer import Offer, OfferStatus
from app.services.deal_service import DealService


BUYER_ID = 6
MERCHANT_ID = 4


def test_buyer_approval_confirms_deal_and_records_timestamp():
    db = SessionLocal()
    request = offer = room = deal = None

    try:
        request = BuyerRequest(
            buyer_id=BUYER_ID,
            title="BUYER APPROVAL TEST",
            description="Temporary approval test",
            status=RequestStatus.NEGOTIATING,
            currency="SDG",
        )
        db.add(request)
        db.flush()

        offer = Offer(
            request_id=request.id,
            merchant_id=MERCHANT_ID,
            listing_id=None,
            amount="600000",
            currency="SDG",
            message="BUYER APPROVAL TEST",
            status=OfferStatus.ACCEPTED,
        )
        db.add(offer)
        db.flush()

        room = NegotiationRoom(
            request_id=request.id,
            offer_id=offer.id,
            status=NegotiationStatus.AGREED,
        )
        db.add(room)
        db.flush()

        deal = Deal(
            request_id=request.id,
            offer_id=offer.id,
            listing_id=None,
            negotiation_room_id=room.id,
            buyer_id=BUYER_ID,
            merchant_id=MERCHANT_ID,
            final_amount=Decimal("600000.00"),
            currency="SDG",
            status=DealStatus.PENDING_BUYER_APPROVAL,
            buyer_approved=False,
        )
        db.add(deal)
        db.commit()
        db.refresh(deal)

        before = datetime.now(timezone.utc)

        approved = DealService.approve_by_buyer(
            db,
            deal,
            buyer_id=BUYER_ID,
        )

        after = datetime.now(timezone.utc)

        assert approved.status == DealStatus.CONFIRMED
        assert approved.buyer_approved is True
        assert approved.approved_at is not None

        approved_at = approved.approved_at
        if approved_at.tzinfo is None:
            approved_at = approved_at.replace(tzinfo=timezone.utc)

        assert before <= approved_at <= after

        print("===== BUYER APPROVAL CONTRACT PASS =====")

    finally:
        if deal is not None:
            db.delete(deal)
            db.commit()
        if room is not None:
            db.delete(room)
            db.commit()
        if offer is not None:
            db.delete(offer)
            db.commit()
        if request is not None:
            db.delete(request)
            db.commit()
        db.close()


if __name__ == "__main__":
    test_buyer_approval_confirms_deal_and_records_timestamp()

def test_non_buyer_cannot_approve_deal():
    db = SessionLocal()
    request = offer = room = deal = None

    try:
        request = BuyerRequest(
            buyer_id=BUYER_ID,
            title="BUYER AUTHORIZATION TEST",
            description="Temporary authorization test",
            status=RequestStatus.NEGOTIATING,
            currency="SDG",
        )
        db.add(request)
        db.flush()

        offer = Offer(
            request_id=request.id,
            merchant_id=MERCHANT_ID,
            listing_id=None,
            amount="600000",
            currency="SDG",
            message="BUYER AUTHORIZATION TEST",
            status=OfferStatus.ACCEPTED,
        )
        db.add(offer)
        db.flush()

        room = NegotiationRoom(
            request_id=request.id,
            offer_id=offer.id,
            status=NegotiationStatus.AGREED,
        )
        db.add(room)
        db.flush()

        deal = Deal(
            request_id=request.id,
            offer_id=offer.id,
            listing_id=None,
            negotiation_room_id=room.id,
            buyer_id=BUYER_ID,
            merchant_id=MERCHANT_ID,
            final_amount=Decimal("600000.00"),
            currency="SDG",
            status=DealStatus.PENDING_BUYER_APPROVAL,
            buyer_approved=False,
        )
        db.add(deal)
        db.commit()
        db.refresh(deal)

        with pytest.raises(PermissionError, match="Only the buyer"):
            DealService.approve_by_buyer(
                db,
                deal,
                buyer_id=MERCHANT_ID,
            )

        db.refresh(deal)
        assert deal.status == DealStatus.PENDING_BUYER_APPROVAL
        assert deal.buyer_approved is False
        assert deal.approved_at is None

        print("===== BUYER AUTHORIZATION PASS =====")

    finally:
        if deal is not None:
            db.delete(deal)
            db.commit()
        if room is not None:
            db.delete(room)
            db.commit()
        if offer is not None:
            db.delete(offer)
            db.commit()
        if request is not None:
            db.delete(request)
            db.commit()
        db.close()


def test_approved_deal_cannot_be_approved_again():
    db = SessionLocal()
    request = offer = room = deal = None

    try:
        request = BuyerRequest(
            buyer_id=BUYER_ID,
            title="BUYER REAPPROVAL TEST",
            description="Temporary reapproval test",
            status=RequestStatus.NEGOTIATING,
            currency="SDG",
        )
        db.add(request)
        db.flush()

        offer = Offer(
            request_id=request.id,
            merchant_id=MERCHANT_ID,
            listing_id=None,
            amount="600000",
            currency="SDG",
            message="BUYER REAPPROVAL TEST",
            status=OfferStatus.ACCEPTED,
        )
        db.add(offer)
        db.flush()

        room = NegotiationRoom(
            request_id=request.id,
            offer_id=offer.id,
            status=NegotiationStatus.AGREED,
        )
        db.add(room)
        db.flush()

        deal = Deal(
            request_id=request.id,
            offer_id=offer.id,
            listing_id=None,
            negotiation_room_id=room.id,
            buyer_id=BUYER_ID,
            merchant_id=MERCHANT_ID,
            final_amount=Decimal("600000.00"),
            currency="SDG",
            status=DealStatus.CONFIRMED,
            buyer_approved=True,
        )
        db.add(deal)
        db.commit()
        db.refresh(deal)

        with pytest.raises(ValueError, match="pending buyer approval"):
            DealService.approve_by_buyer(
                db,
                deal,
                buyer_id=BUYER_ID,
            )

        db.refresh(deal)
        assert deal.status == DealStatus.CONFIRMED
        assert deal.buyer_approved is True

        print("===== BUYER REAPPROVAL GUARD PASS =====")

    finally:
        if deal is not None:
            db.delete(deal)
            db.commit()
        if room is not None:
            db.delete(room)
            db.commit()
        if offer is not None:
            db.delete(offer)
            db.commit()
        if request is not None:
            db.delete(request)
            db.commit()
        db.close()
