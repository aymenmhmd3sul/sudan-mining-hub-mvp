import app.models.user
import app.models.listing_category
import app.models.listing
import app.models.listing_location
import app.models.listing_spec
import app.models.listing_media
import app.models.buyer_request
import app.models.request_item
import app.models.offer
import app.models.negotiation
import app.models.deal
import app.models.deal_item
import app.models.commission

from app.db.session import SessionLocal
from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.offer import Offer, OfferStatus
from app.models.negotiation import NegotiationRoom, NegotiationStatus
from app.models.deal import Deal, DealStatus
from app.services.negotiation_service import NegotiationService


BUYER_ID = 6
MERCHANT_1_ID = 4
MERCHANT_2_ID = 5


def test_accept_offer_creates_pending_deal():
    db = SessionLocal()

    request = None
    offer_winner = None
    offer_competitor = None
    room_winner = None
    room_competitor = None
    deal = None

    try:
        request = BuyerRequest(
            buyer_id=BUYER_ID,
            title="D12 Accepted Offer → Deal Bridge Test",
            description="Temporary integration test",
            status=RequestStatus.OPEN,
            currency="SDG",
        )
        db.add(request)
        db.commit()
        db.refresh(request)

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

        room_winner = NegotiationRoom(
            request_id=request.id,
            offer_id=offer_winner.id,
            status=NegotiationStatus.OPEN,
        )

        room_competitor = NegotiationRoom(
            request_id=request.id,
            offer_id=offer_competitor.id,
            status=NegotiationStatus.OPEN,
        )

        db.add_all([room_winner, room_competitor])
        db.commit()
        db.refresh(room_winner)
        db.refresh(room_competitor)

        result_room = NegotiationService.accept_offer(
            db,
            offer_id=offer_winner.id,
            buyer_id=BUYER_ID,
        )

        db.refresh(offer_winner)
        db.refresh(offer_competitor)
        db.refresh(room_winner)
        db.refresh(room_competitor)

        deal = (
            db.query(Deal)
            .filter(Deal.offer_id == offer_winner.id)
            .first()
        )

        assert result_room.id == room_winner.id

        assert offer_winner.status == OfferStatus.ACCEPTED
        assert room_winner.status == NegotiationStatus.AGREED

        assert offer_competitor.status == OfferStatus.REJECTED
        assert room_competitor.status == NegotiationStatus.CLOSED

        assert deal is not None, (
            "ACCEPTED OFFER did not create a Deal"
        )

        assert deal.request_id == request.id
        assert deal.offer_id == offer_winner.id
        assert deal.negotiation_room_id == room_winner.id
        assert deal.buyer_id == BUYER_ID
        assert deal.merchant_id == MERCHANT_1_ID
        assert str(deal.final_amount) == "600000.00"
        assert deal.currency == "SDG"
        assert deal.status == DealStatus.PENDING_BUYER_APPROVAL
        assert deal.buyer_approved is False

        print("===== D12 NEGOTIATION → DEAL BRIDGE PASS =====")

    finally:
        if deal is not None:
            db.delete(deal)
            db.commit()

        if room_winner is not None:
            db.delete(room_winner)
        if room_competitor is not None:
            db.delete(room_competitor)
        db.commit()

        if offer_winner is not None:
            db.delete(offer_winner)
        if offer_competitor is not None:
            db.delete(offer_competitor)
        db.commit()

        if request is not None:
            db.delete(request)
            db.commit()

        db.close()


if __name__ == "__main__":
    test_accept_offer_creates_pending_deal()
