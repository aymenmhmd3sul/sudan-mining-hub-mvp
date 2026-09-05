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


def _create_confirmed_deal(db):
    request = BuyerRequest(
        buyer_id=BUYER_ID,
        title="MERCHANT DELIVERY TEST",
        description="Temporary merchant delivery test",
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
        message="MERCHANT DELIVERY TEST",
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

    return request, offer, room, deal


def test_merchant_can_mark_confirmed_deal_as_delivered():
    db = SessionLocal()
    request = offer = room = deal = None

    try:
        request, offer, room, deal = _create_confirmed_deal(db)

        before = datetime.now(timezone.utc)

        result = DealService.mark_delivered(
            db,
            deal,
            merchant_id=MERCHANT_ID,
        )

        after = datetime.now(timezone.utc)

        assert result.status == DealStatus.DELIVERED
        assert result.delivered_at is not None
        assert before <= result.delivered_at <= after

        print("===== MERCHANT DELIVERY PASS =====")

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


def test_non_merchant_cannot_mark_deal_as_delivered():
    db = SessionLocal()
    request = offer = room = deal = None

    try:
        request, offer, room, deal = _create_confirmed_deal(db)

        with pytest.raises(PermissionError, match="Only the merchant"):
            DealService.mark_delivered(
                db,
                deal,
                merchant_id=BUYER_ID,
            )

        db.refresh(deal)

        assert deal.status == DealStatus.CONFIRMED
        assert deal.delivered_at is None

        print("===== MERCHANT DELIVERY AUTH GUARD PASS =====")

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


def test_delivery_cannot_be_repeated():
    db = SessionLocal()
    request = offer = room = deal = None

    try:
        request, offer, room, deal = _create_confirmed_deal(db)

        deal.status = DealStatus.DELIVERED
        deal.delivered_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(deal)

        with pytest.raises(ValueError, match="CONFIRMED"):
            DealService.mark_delivered(
                db,
                deal,
                merchant_id=MERCHANT_ID,
            )

        db.refresh(deal)

        assert deal.status == DealStatus.DELIVERED
        assert deal.delivered_at is not None

        print("===== MERCHANT DELIVERY REPEAT GUARD PASS =====")

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
