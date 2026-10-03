import uuid
from datetime import datetime, timezone

import app.db.base  # noqa: F401
from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.main import app
from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.listing import Listing, ListingStatus, ListingType, QuantityMode
from app.models.listing_category import ListingCategory
from app.models.negotiation import (
    NegotiationParticipant,
    NegotiationRoom,
    NegotiationStatus,
)
from app.models.subscription import Subscription
from app.models.user import UserModel, UserRole
from app.services.subscription_service import SubscriptionService


def test_merchant_can_approve_open_negotiation_http():
    marker = f"NEG_APPROVAL_{uuid.uuid4().hex}"
    password = "negotiation-approval-test"

    db = SessionLocal()

    buyer = None
    merchant = None
    category = None
    listing = None
    request_id = None
    room_id = None

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
            description=f"{marker} negotiation approval category",
        )
        db.add(category)
        db.flush()

        listing = Listing(
            owner_id=merchant.id,
            category_id=category.category_id,
            title=f"{marker} Listing",
            description=f"{marker} negotiation approval listing",
            listing_type=ListingType.ASSET,
            quantity_mode=QuantityMode.SINGLE,
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
        # 5. Buyer starts negotiation through the real API.
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
        # 6. Verify the room is correctly shared.
        # ------------------------------------------------------------
        db.expire_all()

        room = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.id == room_id)
            .one()
        )

        request = (
            db.query(BuyerRequest)
            .filter(BuyerRequest.id == request_id)
            .one()
        )

        participants = (
            db.query(NegotiationParticipant)
            .filter(NegotiationParticipant.room_id == room_id)
            .all()
        )

        participant_ids = {participant.user_id for participant in participants}

        assert room.status == NegotiationStatus.OPEN
        assert room.merchant_approved_at is None
        assert request.status == RequestStatus.OPEN
        assert participant_ids == {buyer.id, merchant.id}

        # ------------------------------------------------------------
        # 7. Merchant approves negotiation through the real HTTP API.
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

        approved_at_response = datetime.fromisoformat(
            approve_data["merchant_approved_at"].replace("Z", "+00:00")
        )

        assert approved_at_response.tzinfo is not None

        # ------------------------------------------------------------
        # 8. DB acceptance verification.
        # ------------------------------------------------------------
        db.expire_all()

        saved_room = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.id == room_id)
            .one()
        )

        assert saved_room.status == NegotiationStatus.OPEN
        assert saved_room.merchant_approved_at is not None
        assert saved_room.merchant_approved_at.tzinfo is not None

        # Approval must not create an offer or deal.
        assert saved_room.offer_id is None

        # ------------------------------------------------------------
        # 9. Re-approval is idempotent.
        # ------------------------------------------------------------
        original_approved_at = saved_room.merchant_approved_at

        approve_again = merchant_client.post(
            f"/api/v1/negotiation/{room_id}/approve"
        )

        assert approve_again.status_code == 200, approve_again.text

        db.expire_all()

        reapproved_room = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.id == room_id)
            .one()
        )

        assert reapproved_room.status == NegotiationStatus.OPEN
        assert reapproved_room.merchant_approved_at == original_approved_at

        print("\n===== NEGOTIATION APPROVAL HTTP PASS =====")

    finally:
        # ------------------------------------------------------------
        # 10. Independent cleanup.
        # ------------------------------------------------------------
        if db.is_active:
            try:
                db.rollback()
            except Exception:
                pass

        if room_id is not None:
            db.query(NegotiationParticipant).filter(
                NegotiationParticipant.room_id == room_id
            ).delete(synchronize_session=False)

            db.query(NegotiationRoom).filter(
                NegotiationRoom.id == room_id
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
        # 11. Independent zero-trace verification.
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

        print("===== CLEANUP VERIFICATION =====")
        print("TEST USERS REMAINING:", remaining_users)
        print("TEST CATEGORIES REMAINING:", remaining_categories)
        print("TEST LISTINGS REMAINING:", remaining_listings)
        print("TEST REQUESTS REMAINING:", remaining_requests)
        print("TEST ROOMS REMAINING:", remaining_rooms)

        assert remaining_users == 0
        assert remaining_categories == 0
        assert remaining_listings == 0
        assert remaining_requests == 0
        assert remaining_rooms == 0

        db.close()
