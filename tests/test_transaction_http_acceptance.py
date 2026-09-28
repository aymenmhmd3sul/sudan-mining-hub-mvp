import uuid
from decimal import Decimal

import app.db.base  # noqa: F401
from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.main import app
from app.models.user import UserModel, UserRole
from app.models.listing_category import ListingCategory
from app.models.listing import Listing, ListingStatus, ListingType
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.request_item import RequestItem
from app.models.offer import Offer, OfferStatus
from app.models.offer_item import OfferItem
from app.models.negotiation import NegotiationParticipant, NegotiationRoom
from app.models.deal import Deal, DealStatus
from app.models.commission import Commission
from app.services.subscription_service import SubscriptionService


def test_full_transaction_http_acceptance_isolation():
    marker = f"TX_HTTP_{uuid.uuid4().hex}"
    password = "transaction-http-test"

    db = SessionLocal()

    buyer = None
    merchant = None
    category = None
    listing = None

    request_id = None
    request_item_id = None
    offer_id = None
    room_id = None
    deal_id = None
    commission_id = None

    try:
        # ------------------------------------------------------------
        # 1. Isolated users.
        # ------------------------------------------------------------
        password_hash = get_password_hash(password)

        buyer = UserModel(
            email=f"{marker.lower()}_buyer@example.com",
            hashed_password=password_hash,
            full_name=f"{marker} Buyer",
            role=UserRole.BUYER,
            is_approved=True,
            email_verified=True,
        )

        merchant = UserModel(
            email=f"{marker.lower()}_merchant@example.com",
            hashed_password=password_hash,
            full_name=f"{marker} Merchant",
            role=UserRole.MERCHANT,
            is_approved=True,
            email_verified=True,
        )

        db.add_all([buyer, merchant])
        db.flush()

        # ------------------------------------------------------------
        # 2. Active subscriptions required by transaction APIs.
        # ------------------------------------------------------------
        SubscriptionService.activate(
            db,
            user_id=buyer.id,
            plan=f"{marker}-buyer",
        )

        SubscriptionService.activate(
            db,
            user_id=merchant.id,
            plan=f"{marker}-merchant",
        )

        db.commit()

        # ------------------------------------------------------------
        # 3. Isolated category + active negotiable listing.
        # ------------------------------------------------------------
        category = ListingCategory(
            name=f"{marker} Category",
            status="ACTIVE",
            description=f"{marker} HTTP acceptance category",
        )
        db.add(category)
        db.flush()

        listing = Listing(
            owner_id=merchant.id,
            category_id=category.category_id,
            title=f"{marker} Listing",
            description=f"{marker} HTTP acceptance listing",
            listing_type=ListingType.ASSET,
            price=1000.0,
            currency="USD",
            is_negotiable=True,
            status=ListingStatus.ACTIVE,
            version=1,
        )
        db.add(listing)
        db.commit()
        db.refresh(listing)

        # ------------------------------------------------------------
        # 4. Merchant login through the real HTTP auth route.
        # ------------------------------------------------------------
        merchant_client = TestClient(app)

        merchant_login = merchant_client.post(
            "/auth/login",
            json={
                "email": merchant.email,
                "password": password,
            },
        )

        assert merchant_login.status_code == 200, merchant_login.text
        assert merchant_login.json()["token_type"] == "bearer"
        assert merchant_client.cookies.get("access_token") is not None

        # ------------------------------------------------------------
        # 5. Buyer login through the real HTTP auth route.
        # ------------------------------------------------------------
        buyer_client = TestClient(app)

        buyer_login = buyer_client.post(
            "/auth/login",
            json={
                "email": buyer.email,
                "password": password,
            },
        )

        assert buyer_login.status_code == 200, buyer_login.text
        assert buyer_login.json()["token_type"] == "bearer"
        assert buyer_client.cookies.get("access_token") is not None

        # ------------------------------------------------------------
        # 6. Buyer starts negotiation through the real API.
        # ------------------------------------------------------------
        negotiate = buyer_client.post(
            f"/api/v1/listings/{listing.id}/negotiate"
        )

        assert negotiate.status_code == 200, negotiate.text

        negotiate_data = negotiate.json()

        assert negotiate_data["request_id"] is not None
        assert negotiate_data["listing_id"] == listing.id
        assert negotiate_data["existing"] is False

        request_id = negotiate_data["request_id"]

        request_item = (
            db.query(RequestItem)
            .filter(RequestItem.request_id == request_id)
            .one()
        )
        request_item_id = request_item.id

        # ------------------------------------------------------------
        # 7. Merchant creates the offer through the real API.
        # ------------------------------------------------------------
        create_offer = merchant_client.post(
            "/api/v1/offers",
            json={
                "request_id": request_id,
                "currency": "USD",
                "message": f"{marker} HTTP offer",
                "status": "SUBMITTED",
                "items": [
                    {
                        "request_item_id": request_item_id,
                        "listing_id": listing.id,
                        "quantity": 1,
                        "unit_price": "900.00",
                    }
                ],
            },
        )

        assert create_offer.status_code == 201, create_offer.text

        offer_data = create_offer.json()

        assert offer_data["request_id"] == request_id
        assert offer_data["merchant_id"] == merchant.id
        assert offer_data["currency"] == "USD"
        assert offer_data["status"] == "SUBMITTED"
        assert len(offer_data["items"]) == 1

        offer_id = offer_data["id"]
        room_id = None

        room = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.offer_id == offer_id)
            .one()
        )
        room_id = room.id

        # ------------------------------------------------------------
        # 8. Merchant finalizes through the real HTTP API.
        # ------------------------------------------------------------
        finalize = merchant_client.post(
            f"/api/v1/negotiation/offers/{offer_id}/finalize"
        )

        assert finalize.status_code == 200, finalize.text

        finalize_data = finalize.json()

        assert finalize_data["offer_id"] == offer_id
        assert finalize_data["room_id"] == room_id
        assert finalize_data["room_status"] == "AGREED"
        assert finalize_data["deal_id"] is not None
        assert finalize_data["deal_status"] == "PENDING_BUYER_APPROVAL"
        assert finalize_data["final_amount"] == "900.00"
        assert finalize_data["currency"] == "USD"
        assert finalize_data["commission"] is not None

        deal_id = finalize_data["deal_id"]

        commission = (
            db.query(Commission)
            .filter(Commission.deal_id == deal_id)
            .one()
        )
        commission_id = commission.id

        # ------------------------------------------------------------
        # 9. Buyer accepts through the real HTTP API.
        # ------------------------------------------------------------
        accept = buyer_client.post(
            f"/api/v1/negotiation/offers/{offer_id}/accept"
        )

        assert accept.status_code == 200, accept.text

        accept_data = accept.json()

        assert accept_data["offer_id"] == offer_id
        assert accept_data["room_id"] == room_id
        assert accept_data["room_status"] == "CLOSED"
        assert accept_data["deal_id"] == deal_id
        assert accept_data["deal_status"] == "CONFIRMED"

        # ------------------------------------------------------------
        # 10. Final DB acceptance verification.
        # ------------------------------------------------------------
        db.expire_all()

        saved_offer = db.query(Offer).filter(Offer.id == offer_id).one()
        saved_room = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.id == room_id)
            .one()
        )
        saved_request = (
            db.query(BuyerRequest)
            .filter(BuyerRequest.id == request_id)
            .one()
        )
        saved_listing = (
            db.query(Listing)
            .filter(Listing.id == listing.id)
            .one()
        )
        saved_deal = db.query(Deal).filter(Deal.id == deal_id).one()
        saved_commission = (
            db.query(Commission)
            .filter(Commission.id == commission_id)
            .one()
        )

        assert saved_offer.status == OfferStatus.ACCEPTED
        assert saved_room.status.value == "CLOSED"
        assert saved_request.status == RequestStatus.NEGOTIATING
        assert saved_listing.status == ListingStatus.SOLD
        assert saved_listing.version == 2
        assert saved_deal.status == DealStatus.CONFIRMED
        assert Decimal(str(saved_deal.final_amount)) == Decimal("900.00")
        assert saved_commission.final_amount is not None

        print("\n===== FULL TRANSACTION HTTP ACCEPTANCE PASS =====")

    finally:
        # ------------------------------------------------------------
        # 11. Independent cleanup.
        # ------------------------------------------------------------
        if db.is_active:
            try:
                db.rollback()
            except Exception:
                pass

        if commission_id is not None:
            db.query(Commission).filter(
                Commission.id == commission_id
            ).delete(synchronize_session=False)

        if deal_id is not None:
            db.query(Deal).filter(
                Deal.id == deal_id
            ).delete(synchronize_session=False)

        if room_id is not None:
            db.query(NegotiationParticipant).filter(
                NegotiationParticipant.room_id == room_id
            ).delete(synchronize_session=False)

            db.query(NegotiationRoom).filter(
                NegotiationRoom.id == room_id
            ).delete(synchronize_session=False)

        if offer_id is not None:
            db.query(OfferItem).filter(
                OfferItem.offer_id == offer_id
            ).delete(synchronize_session=False)

            db.query(Offer).filter(
                Offer.id == offer_id
            ).delete(synchronize_session=False)

        if request_item_id is not None:
            db.query(RequestItem).filter(
                RequestItem.id == request_item_id
            ).delete(synchronize_session=False)

        if request_id is not None:
            db.query(BuyerRequest).filter(
                BuyerRequest.id == request_id
            ).delete(synchronize_session=False)

        if listing is not None:
            db.query(Listing).filter(
                Listing.id == listing.id
            ).delete(synchronize_session=False)

        if category is not None:
            db.query(ListingCategory).filter(
                ListingCategory.category_id == category.category_id
            ).delete(synchronize_session=False)

        if buyer is not None:
            db.query(Subscription).filter(
                Subscription.user_id == buyer.id
            ).delete(synchronize_session=False)

        if merchant is not None:
            db.query(Subscription).filter(
                Subscription.user_id == merchant.id
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

        # ------------------------------------------------------------
        # 12. Independent zero-trace verification.
        # ------------------------------------------------------------
        remaining_users = db.query(UserModel).filter(
            UserModel.email.in_(
                [
                    f"{marker.lower()}_buyer@example.com",
                    f"{marker.lower()}_merchant@example.com",
                ]
            )
        ).count()

        remaining_categories = db.query(ListingCategory).filter(
            ListingCategory.name == f"{marker} Category"
        ).count()

        remaining_listings = db.query(Listing).filter(
            Listing.title == f"{marker} Listing"
        ).count()

        remaining_requests = db.query(BuyerRequest).filter(
            BuyerRequest.id == request_id
        ).count() if request_id is not None else 0

        remaining_offers = db.query(Offer).filter(
            Offer.id == offer_id
        ).count() if offer_id is not None else 0

        remaining_rooms = db.query(NegotiationRoom).filter(
            NegotiationRoom.id == room_id
        ).count() if room_id is not None else 0

        remaining_deals = db.query(Deal).filter(
            Deal.id == deal_id
        ).count() if deal_id is not None else 0

        remaining_commissions = db.query(Commission).filter(
            Commission.id == commission_id
        ).count() if commission_id is not None else 0

        print("===== CLEANUP VERIFICATION =====")
        print("TEST USERS REMAINING:", remaining_users)
        print("TEST CATEGORIES REMAINING:", remaining_categories)
        print("TEST LISTINGS REMAINING:", remaining_listings)
        print("TEST REQUESTS REMAINING:", remaining_requests)
        print("TEST OFFERS REMAINING:", remaining_offers)
        print("TEST ROOMS REMAINING:", remaining_rooms)
        print("TEST DEALS REMAINING:", remaining_deals)
        print("TEST COMMISSIONS REMAINING:", remaining_commissions)

        assert remaining_users == 0
        assert remaining_categories == 0
        assert remaining_listings == 0
        assert remaining_requests == 0
        assert remaining_offers == 0
        assert remaining_rooms == 0
        assert remaining_deals == 0
        assert remaining_commissions == 0

        db.close()
