import app.db.base

from decimal import Decimal

import pytest

from app.db.session import SessionLocal
from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.deal import Deal, DealStatus
from app.models.negotiation import NegotiationRoom, NegotiationStatus
from app.models.offer import Offer, OfferStatus
from app.models.commission import CommissionStatus
from app.services.commission_service import CommissionService


BUYER_ID = 6
MERCHANT_ID = 4


def _create_confirmed_deal(db):
    request = BuyerRequest(
        buyer_id=BUYER_ID,
        title="COMMISSION MERCHANT ACCEPTANCE TEST",
        description="Temporary commission lifecycle test",
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
        message="COMMISSION MERCHANT ACCEPTANCE TEST",
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
    db.flush()

    commission = CommissionService.create(
        db,
        deal_id=deal.id,
        merchant_id=MERCHANT_ID,
        proposed_amount=None,
        proposed_currency=None,
        proposed_rate=None,
        platform_amount=Decimal("6000.00"),
        platform_rate=Decimal("1.0000"),
        minimum_amount=Decimal("0.00"),
        final_amount=Decimal("6000.00"),
        currency="SDG",
        adjusted_by_platform=False,
    )

    db.commit()
    db.refresh(deal)
    db.refresh(commission)

    return request, offer, room, deal, commission


def _cleanup(db, request, offer, room, deal, commission):
    if commission is not None:
        db.delete(commission)
        db.commit()
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


def test_commission_requires_merchant_acceptance_before_due():
    db = SessionLocal()
    request = offer = room = deal = commission = None

    try:
        request, offer, room, deal, commission = _create_confirmed_deal(db)

        assert commission.status == CommissionStatus.CALCULATED
        assert commission.merchant_accepted is False

        with pytest.raises(
            ValueError,
            match="Merchant must accept the commission before it becomes DUE",
        ):
            CommissionService.mark_due(db, commission)

        db.refresh(commission)

        assert commission.status == CommissionStatus.CALCULATED
        assert commission.merchant_accepted is False

        accepted = CommissionService.accept_by_merchant(
            db,
            commission,
            MERCHANT_ID,
        )

        assert accepted.merchant_accepted is True
        assert accepted.status == CommissionStatus.CALCULATED

        due = CommissionService.mark_due(db, commission)

        assert due.merchant_accepted is True
        assert due.status == CommissionStatus.DUE

        print("===== COMMISSION MERCHANT ACCEPTANCE LIFECYCLE PASS =====")

    finally:
        _cleanup(db, request, offer, room, deal, commission)
        db.close()


def test_wrong_merchant_cannot_accept_commission():
    db = SessionLocal()
    request = offer = room = deal = commission = None

    try:
        request, offer, room, deal, commission = _create_confirmed_deal(db)

        with pytest.raises(
            PermissionError,
            match="Only the merchant can accept this commission",
        ):
            CommissionService.accept_by_merchant(
                db,
                commission,
                BUYER_ID,
            )

        db.refresh(commission)

        assert commission.merchant_accepted is False
        assert commission.status == CommissionStatus.CALCULATED

        print("===== COMMISSION MERCHANT AUTH GUARD PASS =====")

    finally:
        _cleanup(db, request, offer, room, deal, commission)
        db.close()


def test_commission_acceptance_cannot_be_repeated():
    db = SessionLocal()
    request = offer = room = deal = commission = None

    try:
        request, offer, room, deal, commission = _create_confirmed_deal(db)

        CommissionService.accept_by_merchant(
            db,
            commission,
            MERCHANT_ID,
        )

        with pytest.raises(
            ValueError,
            match="already been accepted",
        ):
            CommissionService.accept_by_merchant(
                db,
                commission,
                MERCHANT_ID,
            )

        db.refresh(commission)

        assert commission.merchant_accepted is True
        assert commission.status == CommissionStatus.CALCULATED

        print("===== COMMISSION ACCEPTANCE REPEAT GUARD PASS =====")

    finally:
        _cleanup(db, request, offer, room, deal, commission)
        db.close()
