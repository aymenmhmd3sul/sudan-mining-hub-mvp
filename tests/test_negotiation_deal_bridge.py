import app.db.base

from app.db.session import SessionLocal
from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.offer import Offer, OfferStatus
from app.models.negotiation import NegotiationRoom, NegotiationStatus
from app.models.deal import Deal, DealStatus
from app.services.negotiation_service import NegotiationService


BUYER_ID = 6
MERCHANT_1_ID = 4
MERCHANT_2_ID = 5


def test_accept_offer_uses_existing_request_room_and_creates_pending_deal():
    db = SessionLocal()

    request = None
    offer_winner = None
    offer_competitor = None
    room = None
    deal = None

    try:
        request = BuyerRequest(
            buyer_id=BUYER_ID,
            title="D12 Existing Room → Accepted Offer → Deal",
            description="Temporary integration test",
            status=RequestStatus.OPEN,
            currency="SDG",
        )
        db.add(request)
        db.commit()
        db.refresh(request)

        room = NegotiationRoom(
            request_id=request.id,
            offer_id=None,
            status=NegotiationStatus.OPEN,
        )
        db.add(room)
        db.commit()
        db.refresh(room)

        original_room_id = room.id

        offer_winner = Offer(
            request_id=request.id,
            merchant_id=MERCHANT_1_ID,
            listing_id=None,
            amount="600000",
            currency="SDG",
            message="Winning offer",
            status=OfferStatus.SUBMITTED,
        )

        offer_competitor = Offer(
            request_id=request.id,
            merchant_id=MERCHANT_2_ID,
            listing_id=None,
            amount="550000",
            currency="SDG",
            message="Competing offer",
            status=OfferStatus.SUBMITTED,
        )

        db.add_all([offer_winner, offer_competitor])
        db.commit()
        db.refresh(offer_winner)
        db.refresh(offer_competitor)

        rooms_before = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.request_id == request.id)
            .count()
        )

        result_room = NegotiationService.accept_offer(
            db,
            offer_id=offer_winner.id,
            buyer_id=BUYER_ID,
        )

        db.refresh(offer_winner)
        db.refresh(offer_competitor)
        db.refresh(room)

        deal = (
            db.query(Deal)
            .filter(Deal.offer_id == offer_winner.id)
            .first()
        )

        rooms_after = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.request_id == request.id)
            .count()
        )

        assert result_room.id == original_room_id
        assert rooms_before == 1
        assert rooms_after == 1

        assert offer_winner.status == OfferStatus.ACCEPTED
        assert room.offer_id == offer_winner.id
        assert room.status == NegotiationStatus.AGREED

        assert offer_competitor.status == OfferStatus.REJECTED

        assert deal is not None
        assert deal.request_id == request.id
        assert deal.offer_id == offer_winner.id
        assert deal.negotiation_room_id == room.id
        assert deal.buyer_id == BUYER_ID
        assert deal.merchant_id == MERCHANT_1_ID
        assert str(deal.final_amount) == "600000.00"
        assert deal.currency == "SDG"
        assert deal.status == DealStatus.PENDING_BUYER_APPROVAL
        assert deal.buyer_approved is False

        print("===== D12 EXISTING ROOM → DEAL BRIDGE PASS =====")

    finally:
        if deal is not None:
            db.delete(deal)
            db.commit()

        if room is not None:
            db.delete(room)
            db.commit()

        if offer_winner is not None:
            db.delete(offer_winner)
            db.commit()

        if offer_competitor is not None:
            db.delete(offer_competitor)
            db.commit()

        if request is not None:
            db.delete(request)
            db.commit()

        db.close()


if __name__ == "__main__":
    test_accept_offer_uses_existing_request_room_and_creates_pending_deal()
