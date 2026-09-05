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


def _create_delivered_deal(db):
    request = BuyerRequest(
        buyer_id=BUYER_ID,
        title="TEST BUYER RECEIPT",
        description="Temporary receipt test",
        status=RequestStatus.NEGOTIATING,
        currency="SDG",
    )
    db.add(request)
    db.flush()

    offer = Offer(
        request_id=request.id,
        merchant_id=MERCHANT_ID,
        amount=Decimal("600000.00"),
        currency="SDG",
        status=OfferStatus.ACCEPTED,
        message="Receipt test offer",
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
        status=DealStatus.DELIVERED,
        buyer_approved=True,
        delivered_at=datetime.now(timezone.utc),
    )
    db.add(deal)
    db.commit()
    db.refresh(deal)

    return request, offer, room, deal


def _cleanup(db, request, offer, room, deal):
    db.query(Deal).filter(Deal.id == deal.id).delete()
    db.query(NegotiationRoom).filter(NegotiationRoom.id == room.id).delete()
    db.query(Offer).filter(Offer.id == offer.id).delete()
    db.query(BuyerRequest).filter(BuyerRequest.id == request.id).delete()
    db.commit()


def test_buyer_can_receive_delivered_deal():
    db = SessionLocal()
    request = offer = room = deal = None

    try:
        request, offer, room, deal = _create_delivered_deal(db)

        before = datetime.now(timezone.utc)

        result = DealService.mark_received(
            db,
            deal,
            buyer_id=BUYER_ID,
        )

        after = datetime.now(timezone.utc)

        assert result.status == DealStatus.COMPLETED
        assert result.received_at is not None
        assert result.completed_at is not None
        assert before <= result.received_at <= after
        assert before <= result.completed_at <= after

    finally:
        if request is not None:
            _cleanup(db, request, offer, room, deal)
        db.close()


def test_non_buyer_cannot_receive_deal():
    db = SessionLocal()
    request = offer = room = deal = None

    try:
        request, offer, room, deal = _create_delivered_deal(db)

        with pytest.raises(
            PermissionError,
            match="Only the buyer",
        ):
            DealService.mark_received(
                db,
                deal,
                buyer_id=MERCHANT_ID,
            )

        assert deal.status == DealStatus.DELIVERED
        assert deal.received_at is None
        assert deal.completed_at is None

    finally:
        if request is not None:
            _cleanup(db, request, offer, room, deal)
        db.close()


def test_receipt_cannot_be_repeated():
    db = SessionLocal()
    request = offer = room = deal = None

    try:
        request, offer, room, deal = _create_delivered_deal(db)

        DealService.mark_received(
            db,
            deal,
            buyer_id=BUYER_ID,
        )

        assert deal.status == DealStatus.COMPLETED
        assert deal.received_at is not None
        assert deal.completed_at is not None

        with pytest.raises(
            ValueError,
            match="DELIVERED",
        ):
            DealService.mark_received(
                db,
                deal,
                buyer_id=BUYER_ID,
            )

    finally:
        if request is not None:
            _cleanup(db, request, offer, room, deal)
        db.close()


def test_direct_completion_cannot_bypass_receipt():
    db = SessionLocal()
    request = offer = room = deal = None
    try:
        request, offer, room, deal = _create_delivered_deal(db)

        with pytest.raises(
            ValueError,
            match="receipt",
        ):
            DealService.complete_by_buyer(db, deal)

        db.refresh(deal)
        assert deal.status == DealStatus.DELIVERED
        assert deal.received_at is None
        assert deal.completed_at is None
    finally:
        if request is not None:
            _cleanup(db, request, offer, room, deal)
        db.close()
