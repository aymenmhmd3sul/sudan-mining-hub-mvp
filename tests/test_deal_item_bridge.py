import app.db.base

from decimal import Decimal

from app.db.session import SessionLocal
from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.request_item import RequestItem
from app.models.offer import Offer, OfferStatus
from app.models.offer_item import OfferItem
from app.models.deal import Deal, DealStatus
from app.models.deal_item import DealItem
from app.models.negotiation import NegotiationRoom, NegotiationStatus
from app.services.deal_service import DealService


BUYER_ID = 6
MERCHANT_ID = 4


def test_deal_create_copies_offer_items():
    db = SessionLocal()

    request = None
    request_item = None
    offer = None
    offer_item = None
    room = None
    deal = None

    try:
        request = BuyerRequest(
            buyer_id=BUYER_ID,
            title="DEAL ITEM BRIDGE TEST",
            description="Temporary integration test",
            status=RequestStatus.OPEN,
            currency="SDG",
        )
        db.add(request)
        db.commit()
        db.refresh(request)

        request_item = RequestItem(
            request_id=request.id,
            title="Test Mining Equipment",
            description="Temporary item",
            quantity=2,
            unit="piece",
        )
        db.add(request_item)
        db.commit()
        db.refresh(request_item)

        offer = Offer(
            request_id=request.id,
            merchant_id=MERCHANT_ID,
            listing_id=None,
            amount="600000",
            currency="SDG",
            message="DEAL ITEM BRIDGE",
            status=OfferStatus.ACCEPTED,
        )
        db.add(offer)
        db.commit()
        db.refresh(offer)

        offer_item = OfferItem(
            offer_id=offer.id,
            request_item_id=request_item.id,
            listing_id=None,
            quantity=2,
            unit_price=Decimal("300000.00"),
            total_price=Decimal("600000.00"),
        )
        db.add(offer_item)

        room = NegotiationRoom(
            request_id=request.id,
            offer_id=offer.id,
            status=NegotiationStatus.AGREED,
        )
        db.add(room)
        db.commit()
        db.refresh(offer_item)
        db.refresh(room)

        deal = DealService.create(
            db,
            request_id=request.id,
            offer_id=offer.id,
            listing_id=None,
            negotiation_room_id=room.id,
            buyer_id=BUYER_ID,
            merchant_id=MERCHANT_ID,
            final_amount=Decimal("600000.00"),
            currency="SDG",
        )

        deal_item = (
            db.query(DealItem)
            .filter(DealItem.deal_id == deal.id)
            .first()
        )

        assert deal.status == DealStatus.PENDING_BUYER_APPROVAL
        assert deal_item is not None
        assert deal_item.request_item_id == request_item.id
        assert deal_item.quantity == 2
        assert str(deal_item.unit_price) == "300000.00"
        assert str(deal_item.total_price) == "600000.00"

        print("===== DEAL ITEM BRIDGE PASS =====")

    finally:
        if deal is not None:
            db.query(DealItem).filter(DealItem.deal_id == deal.id).delete(
                synchronize_session=False
            )
            db.delete(deal)
            db.commit()

        if room is not None:
            db.delete(room)
            db.commit()

        if offer_item is not None:
            db.delete(offer_item)
            db.commit()

        if offer is not None:
            db.delete(offer)
            db.commit()

        if request_item is not None:
            db.delete(request_item)
            db.commit()

        if request is not None:
            db.delete(request)
            db.commit()

        db.close()


if __name__ == "__main__":
    test_deal_create_copies_offer_items()
