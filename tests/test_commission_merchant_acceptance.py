import app.db.base

from decimal import Decimal
import uuid

import pytest

from app.db.session import SessionLocal
from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.deal import Deal, DealStatus
from app.models.negotiation import NegotiationRoom, NegotiationStatus
from app.models.offer import Offer, OfferStatus
from app.models.commission import Commission, CommissionStatus
from app.models.user import UserModel, UserRole
from app.services.commission_service import CommissionService


def _create_confirmed_deal(db):
    marker = f"COMMISSION_LIFECYCLE_{uuid.uuid4().hex}"
    buyer = UserModel(
        email=f"{marker.lower()}_buyer@example.invalid",
        hashed_password="test-hash",
        full_name=f"{marker} Buyer",
        role=UserRole.BUYER,
        is_approved=True,
        email_verified=True,
    )
    merchant = UserModel(
        email=f"{marker.lower()}_merchant@example.invalid",
        hashed_password="test-hash",
        full_name=f"{marker} Merchant",
        role=UserRole.MERCHANT,
        is_approved=True,
        email_verified=True,
    )
    db.add_all([buyer, merchant])
    db.flush()

    request = BuyerRequest(
        buyer_id=buyer.id,
        title=f"{marker} request",
        description="Temporary commission lifecycle test",
        status=RequestStatus.NEGOTIATING,
        currency="SDG",
    )
    db.add(request)
    db.flush()

    offer = Offer(
        request_id=request.id,
        merchant_id=merchant.id,
        listing_id=None,
        amount="600000",
        currency="SDG",
        message=f"{marker} offer",
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
        buyer_id=buyer.id,
        merchant_id=merchant.id,
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
        merchant_id=merchant.id,
        proposed_amount=None,
        proposed_currency=None,
        proposed_rate=None,
        platform_amount=Decimal("6000.00"),
        platform_rate=Decimal("1.0000"),
        minimum_amount=Decimal("0.00"),
        final_amount=Decimal("6000.00"),
        currency="SDG",
        adjusted_by_platform=True,
    )

    db.commit()
    db.refresh(deal)
    db.refresh(commission)

    return request, offer, room, deal, commission, buyer, merchant


def _cleanup(db, request, offer, room, deal, commission, buyer, merchant):
    if deal is not None:
        db.query(Commission).filter(Commission.deal_id == deal.id).delete(
            synchronize_session=False
        )
    elif commission is not None:
        db.query(Commission).filter(Commission.id == commission.id).delete(
            synchronize_session=False
        )
    if deal is not None:
        db.query(Deal).filter(Deal.id == deal.id).delete(
            synchronize_session=False
        )
    if room is not None:
        db.query(NegotiationRoom).filter(
            NegotiationRoom.id == room.id
        ).delete(synchronize_session=False)
    if offer is not None:
        db.query(Offer).filter(Offer.id == offer.id).delete(
            synchronize_session=False
        )
    if request is not None:
        db.query(BuyerRequest).filter(
            BuyerRequest.id == request.id
        ).delete(synchronize_session=False)
    for user in (buyer, merchant):
        if user is not None:
            db.query(UserModel).filter(UserModel.id == user.id).delete(
                synchronize_session=False
            )
    db.commit()


def test_commission_is_accepted_on_creation_and_can_become_due():
    db = SessionLocal()
    request = offer = room = deal = commission = buyer = merchant = None

    try:
        request, offer, room, deal, commission, buyer, merchant = (
            _create_confirmed_deal(db)
        )

        assert commission.status == CommissionStatus.CALCULATED
        assert commission.merchant_accepted is True
        assert commission.deal_id == deal.id
        assert commission.merchant_id == merchant.id
        assert commission.currency == deal.currency == "SDG"
        assert commission.platform_rate == Decimal("1.0000")
        assert commission.platform_amount == Decimal("6000.00")
        assert commission.final_amount == Decimal("6000.00")
        assert commission.final_amount == (
            deal.final_amount * commission.platform_rate / Decimal("100")
        )

        due = CommissionService.mark_due(db, commission)

        assert due.merchant_accepted is True
        assert due.status == CommissionStatus.DUE

        print("===== COMMISSION MERCHANT ACCEPTANCE LIFECYCLE PASS =====")

    finally:
        _cleanup(db, request, offer, room, deal, commission, buyer, merchant)
        db.close()


def test_wrong_merchant_cannot_accept_commission():
    db = SessionLocal()
    request = offer = room = deal = commission = buyer = merchant = None

    try:
        request, offer, room, deal, commission, buyer, merchant = (
            _create_confirmed_deal(db)
        )

        with pytest.raises(
            PermissionError,
            match="Only the merchant can accept this commission",
        ):
            CommissionService.accept_by_merchant(
                db,
                commission,
                buyer.id,
            )

        db.refresh(commission)

        assert commission.merchant_accepted is True
        assert commission.status == CommissionStatus.CALCULATED

        print("===== COMMISSION MERCHANT AUTH GUARD PASS =====")

    finally:
        _cleanup(db, request, offer, room, deal, commission, buyer, merchant)
        db.close()


def test_already_accepted_commission_cannot_be_accepted_again():
    db = SessionLocal()
    request = offer = room = deal = commission = buyer = merchant = None

    try:
        request, offer, room, deal, commission, buyer, merchant = (
            _create_confirmed_deal(db)
        )
        assert commission.merchant_accepted is True

        with pytest.raises(
            ValueError,
            match="already been accepted",
        ):
            CommissionService.accept_by_merchant(
                db,
                commission,
                merchant.id,
            )

        db.refresh(commission)

        assert commission.merchant_accepted is True
        assert commission.status == CommissionStatus.CALCULATED

        print("===== COMMISSION ACCEPTANCE REPEAT GUARD PASS =====")

    finally:
        _cleanup(db, request, offer, room, deal, commission, buyer, merchant)
        db.close()
