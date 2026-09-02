from decimal import Decimal

from app.db.base import BuyerRequest
from app.db.session import SessionLocal
from app.models.offer import OfferStatus
from app.models.offer_item import OfferItem
from app.models.request_item import RequestItem
from app.models.user import UserModel
from app.services.offer_service import OfferService


def test_offer_service_create_and_items_contract():
    db = SessionLocal()
    try:
        merchant = db.query(UserModel).filter(UserModel.id == 4).first()
        buyer = db.query(UserModel).filter(UserModel.id == 6).first()

        assert merchant is not None, "Test requires merchant user id=4"
        assert buyer is not None, "Test requires buyer user id=6"

        request = BuyerRequest(
            buyer_id=buyer.id,
            title="isolated multi-item contract test",
            status="NEGOTIATING",
            currency="SDG",
        )
        db.add(request)
        db.flush()

        item1 = RequestItem(
            request_id=request.id,
            title="test item 1",
            quantity=2,
            unit="unit",
        )
        item2 = RequestItem(
            request_id=request.id,
            title="test item 2",
            quantity=3,
            unit="unit",
        )
        db.add_all([item1, item2])
        db.flush()

        offer = OfferService.create(
            db,
            request_id=request.id,
            merchant_id=merchant.id,
            currency="SDG",
            message="isolated multi-item contract test",
            status=OfferStatus.DRAFT,
            items=[
                {
                    "request_item_id": item1.id,
                    "listing_id": None,
                    "quantity": 2,
                    "unit_price": Decimal("75000.00"),
                },
                {
                    "request_item_id": item2.id,
                    "listing_id": None,
                    "quantity": 3,
                    "unit_price": Decimal("50000.00"),
                },
            ],
        )

        assert offer.id is not None
        assert offer.amount == "300000.00"
        assert len(offer.items) == 2
        assert offer.items[0].total_price == Decimal("150000.00")
        assert offer.items[1].total_price == Decimal("150000.00")

        db.rollback()
        print("MULTI-ITEM SERVICE CONTRACT: PASS")
    finally:
        db.close()
