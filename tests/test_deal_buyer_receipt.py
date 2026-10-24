import app.db.base

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.db.session import SessionLocal
from app.models.user import UserModel, UserRole
from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.deal import Deal, DealStatus
from app.models.negotiation import NegotiationRoom, NegotiationStatus
from app.models.offer import Offer, OfferStatus
from app.services.deal_service import DealService


def _create_delivered_deal(db):
    buyer = None
    merchant = None

    try:
        marker = uuid4().hex

        buyer = UserModel(
            email=f"receipt-buyer-{marker}@example.invalid",
            hashed_password="not-used-test-hash",
            full_name="Temporary Receipt Buyer",
            role=UserRole.BUYER,
            is_approved=True,
            email_verified=True,
        )
        merchant = UserModel(
            email=f"receipt-merchant-{marker}@example.invalid",
            hashed_password="not-used-test-hash",
            full_name="Temporary Receipt Merchant",
            role=UserRole.MERCHANT,
            is_approved=True,
            email_verified=True,
        )

        db.add_all([buyer, merchant])
        db.flush()

        request = BuyerRequest(
            buyer_id=buyer.id,
            title="TEST BUYER RECEIPT",
            description="Temporary receipt test",
            status=RequestStatus.NEGOTIATING,
            currency="SDG",
        )
        db.add(request)
        db.flush()

        offer = Offer(
            request_id=request.id,
            merchant_id=merchant.id,
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
            buyer_id=buyer.id,
            merchant_id=merchant.id,
            final_amount=Decimal("600000.00"),
            currency="SDG",
            status=DealStatus.DELIVERED,
            buyer_approved=True,
            delivered_at=datetime.now(timezone.utc),
        )
        db.add(deal)
        db.commit()
        db.refresh(deal)

        return buyer, merchant, request, offer, room, deal

    except Exception:
        db.rollback()
        raise


def _cleanup(db, buyer, merchant, request, offer, room, deal):
    try:
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
        if buyer is not None:
            db.query(UserModel).filter(
                UserModel.id == buyer.id
            ).delete(synchronize_session=False)
        if merchant is not None:
            db.query(UserModel).filter(
                UserModel.id == merchant.id
            ).delete(synchronize_session=False)

        db.commit()
    except Exception:
        db.rollback()
        raise


def test_buyer_can_receive_delivered_deal():
    db = SessionLocal()
    buyer = merchant = request = offer = room = deal = None

    try:
        buyer, merchant, request, offer, room, deal = (
            _create_delivered_deal(db)
        )

        before = datetime.now(timezone.utc)

        result = DealService.mark_received(
            db,
            deal,
            buyer_id=buyer.id,
        )

        after = datetime.now(timezone.utc)

        assert result.status == DealStatus.COMPLETED
        assert result.received_at is not None
        assert result.completed_at is not None
        assert before <= result.received_at <= after
        assert before <= result.completed_at <= after

    finally:
        if request is not None:
            _cleanup(db, buyer, merchant, request, offer, room, deal)
        else:
            db.rollback()
            if buyer is not None or merchant is not None:
                for user in (buyer, merchant):
                    if user is not None and user.id is not None:
                        db.query(UserModel).filter(
                            UserModel.id == user.id
                        ).delete(synchronize_session=False)
                db.commit()
        db.close()


def test_non_buyer_cannot_receive_deal():
    db = SessionLocal()
    buyer = merchant = request = offer = room = deal = None

    try:
        buyer, merchant, request, offer, room, deal = (
            _create_delivered_deal(db)
        )

        with pytest.raises(
            PermissionError,
            match="Only the buyer",
        ):
            DealService.mark_received(
                db,
                deal,
                buyer_id=merchant.id,
            )

        assert deal.status == DealStatus.DELIVERED
        assert deal.received_at is None
        assert deal.completed_at is None

    finally:
        if request is not None:
            _cleanup(db, buyer, merchant, request, offer, room, deal)
        else:
            db.rollback()
            for user in (buyer, merchant):
                if user is not None and user.id is not None:
                    db.query(UserModel).filter(
                        UserModel.id == user.id
                    ).delete(synchronize_session=False)
            db.commit()
        db.close()


def test_receipt_cannot_be_repeated():
    db = SessionLocal()
    buyer = merchant = request = offer = room = deal = None

    try:
        buyer, merchant, request, offer, room, deal = (
            _create_delivered_deal(db)
        )

        DealService.mark_received(
            db,
            deal,
            buyer_id=buyer.id,
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
                buyer_id=buyer.id,
            )

    finally:
        if request is not None:
            _cleanup(db, buyer, merchant, request, offer, room, deal)
        else:
            db.rollback()
            for user in (buyer, merchant):
                if user is not None and user.id is not None:
                    db.query(UserModel).filter(
                        UserModel.id == user.id
                    ).delete(synchronize_session=False)
            db.commit()
        db.close()


def test_direct_completion_cannot_bypass_receipt():
    db = SessionLocal()
    buyer = merchant = request = offer = room = deal = None

    try:
        buyer, merchant, request, offer, room, deal = (
            _create_delivered_deal(db)
        )

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
            _cleanup(db, buyer, merchant, request, offer, room, deal)
        else:
            db.rollback()
            for user in (buyer, merchant):
                if user is not None and user.id is not None:
                    db.query(UserModel).filter(
                        UserModel.id == user.id
                    ).delete(synchronize_session=False)
            db.commit()
        db.close()
