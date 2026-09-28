import uuid

import app.db.base  # noqa: F401
from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.main import app
from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.commission import Commission, CommissionStatus
from app.models.deal import Deal
from app.models.listing import Listing, ListingStatus, ListingType
from app.models.listing_category import ListingCategory
from app.models.negotiation import (
    NegotiationParticipant,
    NegotiationRoom,
    NegotiationStatus,
)
from app.models.notification import Notification
from app.models.offer import Offer, OfferStatus
from app.models.offer_item import OfferItem
from app.models.request_item import RequestItem
from app.models.subscription import Subscription
from app.models.user import UserModel, UserRole
from app.services.subscription_service import SubscriptionService


def test_merchant_can_finalize_buyer_offer_after_approval_http():
    marker = f"BUYER_OFFER_{uuid.uuid4().hex}"
    password = "buyer-offer-test"

    db = SessionLocal()
    buyer = None
    merchant = None
    category = None
    listing = None
    request_id = None
    room_id = None
    offer_id = None
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
        # 3. Isolated active negotiable listing.
        # ------------------------------------------------------------
        category = ListingCategory(
            name=f"{marker} Category",
            status="ACTIVE",
            description=f"{marker} buyer offer category",
        )
        db.add(category)
        db.flush()

        listing = Listing(
            owner_id=merchant.id,
            category_id=category.category_id,
            title=f"{marker} Listing",
            description=f"{marker} buyer offer listing",
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
        # 4. Real HTTP authentication.
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
        assert merchant_client.cookies.get("access_token") is not None

        buyer_client = TestClient(app)
        buyer_login = buyer_client.post(
            "/auth/login",
            json={
                "email": buyer.email,
                "password": password,
            },
        )
        assert buyer_login.status_code == 200, buyer_login.text
        assert buyer_client.cookies.get("access_token") is not None

        # ------------------------------------------------------------
        # 5. Buyer starts negotiation.
        # ------------------------------------------------------------
        negotiate = buyer_client.post(
            f"/api/v1/listings/{listing.id}/negotiate"
        )
        assert negotiate.status_code == 200, negotiate.text

        negotiate_data = negotiate.json()
        assert negotiate_data["listing_id"] == listing.id
        assert negotiate_data["request_id"] is not None
        assert negotiate_data["status"] == "OPEN"
        assert negotiate_data["existing"] is False

        request_id = negotiate_data["request_id"]
        room_id = negotiate_data["id"]

        # ------------------------------------------------------------
        # 6. Verify RequestItem exists for the offer.
        # ------------------------------------------------------------
        db.expire_all()

        request_item = (
            db.query(RequestItem)
            .filter(RequestItem.request_id == request_id)
            .one()
        )
        assert request_item.title == listing.title

        # ------------------------------------------------------------
        # 7. Before merchant approval, buyer must be rejected.
        # ------------------------------------------------------------
        blocked_offer = buyer_client.post(
            "/api/v1/offers",
            json={
                "room_id": room_id,
                "currency": "USD",
                "message": "Premature buyer offer",
                "items": [
                    {
                        "request_item_id": request_item.id,
                        "listing_id": listing.id,
                        "quantity": 1,
                        "unit_price": 900,
                    }
                ],
            },
        )

        assert blocked_offer.status_code == 400, blocked_offer.text
        assert "Merchant approval" in blocked_offer.text

        # ------------------------------------------------------------
        # 8. Merchant approves the negotiation.
        # ------------------------------------------------------------
        approve = merchant_client.post(
            f"/api/v1/negotiation/{room_id}/approve"
        )
        assert approve.status_code == 200, approve.text

        approve_data = approve.json()
        assert approve_data["room_id"] == room_id
        assert approve_data["request_id"] == request_id
        assert approve_data["status"] == "OPEN"
        assert approve_data["merchant_approved_at"] is not None

        # ------------------------------------------------------------
        # 9. Buyer submits the offer through the new endpoint.
        # ------------------------------------------------------------
        buyer_offer = buyer_client.post(
            "/api/v1/offers",
            json={
                "room_id": room_id,
                "currency": "USD",
                "message": "Buyer final offer after merchant approval",
                "items": [
                    {
                        "request_item_id": request_item.id,
                        "listing_id": listing.id,
                        "quantity": 1,
                        "unit_price": 900,
                    }
                ],
            },
        )

        assert buyer_offer.status_code == 201, buyer_offer.text

        offer_data = buyer_offer.json()

        assert offer_data["room_id"] == room_id
        assert offer_data["request_id"] == request_id
        assert offer_data["merchant_id"] == merchant.id
        assert offer_data["amount"] == "900.00"
        assert offer_data["currency"] == "USD"
        assert offer_data["status"] == "SUBMITTED"
        assert len(offer_data["items"]) == 1
        assert offer_data["items"][0]["request_item_id"] == request_item.id
        assert offer_data["items"][0]["listing_id"] == listing.id
        assert offer_data["items"][0]["quantity"] == 1
        assert offer_data["items"][0]["unit_price"] == "900.00"
        assert offer_data["items"][0]["total_price"] == "900.00"

        offer_id = offer_data["id"]

        # ------------------------------------------------------------
        # 10. DB acceptance: same room, one submitted offer.
        # ------------------------------------------------------------
        db.expire_all()

        saved_room = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.id == room_id)
            .one()
        )
        saved_offer = (
            db.query(Offer)
            .filter(Offer.id == offer_id)
            .one()
        )
        saved_offer_item = (
            db.query(OfferItem)
            .filter(OfferItem.offer_id == offer_id)
            .one()
        )

        assert saved_room.status == NegotiationStatus.OPEN
        assert saved_room.merchant_approved_at is not None
        assert saved_room.offer_id == offer_id

        assert saved_offer.request_id == request_id
        assert saved_offer.merchant_id == merchant.id
        assert saved_offer.listing_id == listing.id
        assert saved_offer.status == OfferStatus.SUBMITTED
        assert saved_offer.amount == "900.00"

        assert saved_offer_item.request_item_id == request_item.id
        assert saved_offer_item.listing_id == listing.id
        assert saved_offer_item.quantity == 1
        assert str(saved_offer_item.unit_price) == "900.00"

        # Exactly one room exists for this request.
        room_count = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.request_id == request_id)
            .count()
        )
        assert room_count == 1

        # The offer belongs to the same negotiation request.
        offer_count = (
            db.query(Offer)
            .filter(Offer.request_id == request_id)
            .count()
        )
        assert offer_count == 1

        # The merchant receives the new-offer notification.
        notification_count = (
            db.query(Notification)
            .filter(
                Notification.recipient_user_id == merchant.id,
                Notification.event_type == "NEW_OFFER",
                Notification.related_type == "offer",
                Notification.related_id == offer_id,
            )
            .count()
        )
        assert notification_count == 1

        # Buyer cannot submit a second offer in the same room.
        duplicate_offer = buyer_client.post(
            "/api/v1/offers",
            json={
                "room_id": room_id,
                "currency": "USD",
                "message": "Duplicate offer",
                "items": [
                    {
                        "request_item_id": request_item.id,
                        "listing_id": listing.id,
                        "quantity": 1,
                        "unit_price": 850,
                    }
                ],
            },
        )

        assert duplicate_offer.status_code == 400, duplicate_offer.text
        assert "already been submitted" in duplicate_offer.text

        # ------------------------------------------------------------
        # 10. Merchant finalizes the buyer's submitted offer.
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

        assert finalize_data["commission"]["final_amount"] == str(
            commission.final_amount
        )
        assert finalize_data["commission"]["currency"] == commission.currency
        assert finalize_data["commission"]["status"] == commission.status

        # ------------------------------------------------------------
        # 11. Database acceptance.
        # ------------------------------------------------------------
        db.expire_all()

        saved_room = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.id == room_id)
            .one()
        )

        saved_offer = (
            db.query(Offer)
            .filter(Offer.id == offer_id)
            .one()
        )

        saved_deal = (
            db.query(Deal)
            .filter(Deal.id == deal_id)
            .one()
        )

        saved_commission = (
            db.query(Commission)
            .filter(Commission.id == commission_id)
            .one()
        )

        assert saved_room.status == NegotiationStatus.AGREED
        assert saved_room.offer_id == offer_id
        assert saved_room.merchant_approved_at is not None

        assert saved_offer.status == OfferStatus.FINAL
        assert saved_offer.request_id == request_id
        assert saved_offer.merchant_id == merchant.id
        assert saved_offer.listing_id == listing.id
        assert str(saved_offer.amount) == "900.00"

        assert saved_deal.offer_id == offer_id
        assert saved_deal.request_id == request_id
        assert saved_deal.status.value == "PENDING_BUYER_APPROVAL"
        assert str(saved_deal.final_amount) == "900.00"
        assert saved_deal.currency == "USD"

        assert saved_commission.deal_id == deal_id
        assert saved_commission.merchant_id == merchant.id
        assert saved_commission.currency == "USD"
        assert saved_commission.status == CommissionStatus.CALCULATED
        assert saved_commission.final_amount is not None

        # Listing remains ACTIVE until the buyer accepts the deal.
        db.expire_all()

        saved_listing = (
            db.query(Listing)
            .filter(Listing.id == listing.id)
            .one()
        )

        assert saved_listing.status == ListingStatus.ACTIVE

        print("\n===== MERCHANT FINALIZE HTTP PASS =====")

    finally:
        # ------------------------------------------------------------
        # 11. Independent cleanup.
        # ------------------------------------------------------------
        try:
            db.rollback()

            if offer_id is not None:


                deal_ids = [


                    row[0]


                    for row in db.query(Deal.id)


                    .filter(Deal.offer_id == offer_id)


                    .all()


                ]



                if deal_ids:


                    db.query(Commission).filter(


                        Commission.deal_id.in_(deal_ids)


                    ).delete(synchronize_session=False)



                    db.query(Deal).filter(


                        Deal.id.in_(deal_ids)


                    ).delete(synchronize_session=False)



                db.query(OfferItem).filter(


                    OfferItem.offer_id == offer_id


                ).delete(synchronize_session=False)



                db.query(Notification).filter(


                    Notification.related_type == "offer",


                    Notification.related_id == offer_id,


                ).delete(synchronize_session=False)



                db.query(Offer).filter(


                    Offer.id == offer_id


                ).delete(synchronize_session=False)



                db.commit()

            if room_id is not None:
                db.query(NegotiationParticipant).filter(
                    NegotiationParticipant.room_id == room_id
                ).delete(synchronize_session=False)

                db.query(NegotiationRoom).filter(
                    NegotiationRoom.id == room_id
                ).delete(synchronize_session=False)

                db.commit()

            if request_id is not None:
                request_item_ids = [
                    row[0]
                    for row in db.query(RequestItem.id).filter(
                        RequestItem.request_id == request_id
                    ).all()
                ]

                if request_item_ids:
                    db.query(OfferItem).filter(
                        OfferItem.request_item_id.in_(request_item_ids)
                    ).delete(synchronize_session=False)

                db.query(RequestItem).filter(
                    RequestItem.request_id == request_id
                ).delete(synchronize_session=False)

                db.query(BuyerRequest).filter(
                    BuyerRequest.id == request_id
                ).delete(synchronize_session=False)

                db.commit()

            if listing is not None:
                db.query(Listing).filter(
                    Listing.id == listing.id
                ).delete(synchronize_session=False)

                db.commit()

            if category is not None:
                db.query(ListingCategory).filter(
                    ListingCategory.category_id == category.category_id
                ).delete(synchronize_session=False)

                db.commit()

            user_ids = [
                user.id
                for user in (buyer, merchant)
                if user is not None
            ]

            if user_ids:
                db.query(Subscription).filter(
                    Subscription.user_id.in_(user_ids)
                ).delete(synchronize_session=False)

                db.query(UserModel).filter(
                    UserModel.id.in_(user_ids)
                ).delete(synchronize_session=False)

                db.commit()

            # --------------------------------------------------------
            # 12. Independent zero-trace verification.
            # --------------------------------------------------------
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

            remaining_requests = (
                db.query(BuyerRequest)
                .filter(BuyerRequest.id == request_id)
                .count()
                if request_id is not None
                else 0
            )

            remaining_rooms = (
                db.query(NegotiationRoom)
                .filter(NegotiationRoom.id == room_id)
                .count()
                if room_id is not None
                else 0
            )

            remaining_offers = (
                db.query(Offer)
                .filter(Offer.id == offer_id)
                .count()
                if offer_id is not None
                else 0
            )

            remaining_notifications = (
                db.query(Notification)
                .filter(
                    Notification.related_type == "offer",
                    Notification.related_id == offer_id,
                )
                .count()
                if offer_id is not None
                else 0
            )

            print("===== CLEANUP VERIFICATION =====")
            print("TEST USERS REMAINING:", remaining_users)
            print("TEST CATEGORIES REMAINING:", remaining_categories)
            print("TEST LISTINGS REMAINING:", remaining_listings)
            print("TEST REQUESTS REMAINING:", remaining_requests)
            print("TEST ROOMS REMAINING:", remaining_rooms)
            print("TEST OFFERS REMAINING:", remaining_offers)
            print("TEST NOTIFICATIONS REMAINING:", remaining_notifications)

            assert remaining_users == 0
            assert remaining_categories == 0
            assert remaining_listings == 0
            assert remaining_requests == 0
            assert remaining_rooms == 0
            assert remaining_offers == 0
            assert remaining_notifications == 0

        finally:
            db.close()
