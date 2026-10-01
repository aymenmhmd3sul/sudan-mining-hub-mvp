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
from app.models.subscription import Subscription
from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.request_item import RequestItem
from app.models.offer import Offer, OfferStatus
from app.models.offer_item import OfferItem
from app.models.negotiation import (
    NegotiationParticipant,
    NegotiationRoom,
    NegotiationStatus,
)
from app.models.deal import Deal, DealStatus
from app.models.deal_item import DealItem
from app.models.commission import Commission, CommissionStatus
from app.models.notification import Notification
from app.services.subscription_service import SubscriptionService


def test_deal_delivery_receipt_commission_http_acceptance_isolation():
    marker = f"DELIVERY_HTTP_{uuid.uuid4().hex}"
    password = "delivery-http-test"

    db = SessionLocal()

    buyer = None
    merchant = None
    category = None
    listing = None

    request_id = None
    request_item_id = None
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
        # 2. Active subscriptions.
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
        # 3. Active negotiable listing.
        # ------------------------------------------------------------
        category = ListingCategory(
            name=f"{marker} Category",
            status="ACTIVE",
            description=f"{marker} delivery acceptance category",
        )
        db.add(category)
        db.flush()

        listing = Listing(
            owner_id=merchant.id,
            category_id=category.category_id,
            title=f"{marker} Listing",
            description=f"{marker} delivery acceptance listing",
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
        buyer_client = TestClient(app)

        merchant_login = merchant_client.post(
            "/auth/login",
            json={
                "email": merchant.email,
                "password": password,
            },
        )
        assert merchant_login.status_code == 200, merchant_login.text
        assert merchant_client.cookies.get("access_token") is not None

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
        request_id = negotiate_data["request_id"]
        room_id = negotiate_data["id"]

        request_item = (
            db.query(RequestItem)
            .filter(RequestItem.request_id == request_id)
            .one()
        )
        request_item_id = request_item.id

        room = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.id == room_id)
            .one()
        )

        assert room.status == NegotiationStatus.OPEN
        assert room.merchant_approved_at is None

        # ------------------------------------------------------------
        # 6. Merchant approves negotiation.
        # ------------------------------------------------------------
        approve = merchant_client.post(
            f"/api/v1/negotiation/{room_id}/approve"
        )
        assert approve.status_code == 200, approve.text
        assert approve.json()["merchant_approved_at"] is not None

        # ------------------------------------------------------------
        # 7. Buyer submits offer.
        # ------------------------------------------------------------
        buyer_offer = buyer_client.post(
            "/api/v1/offers",
            json={
                "room_id": room_id,
                "currency": "USD",
                "message": "Delivery acceptance test offer",
                "items": [
                    {
                        "request_item_id": request_item_id,
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

        offer_id = offer_data["id"]

        # ------------------------------------------------------------
        # 8. Merchant finalizes offer.
        # ------------------------------------------------------------
        finalize = merchant_client.post(
            f"/api/v1/negotiation/offers/{offer_id}/finalize"
        )

        assert finalize.status_code == 200, finalize.text

        finalize_data = finalize.json()

        assert finalize_data["room_status"] == "AGREED"
        assert finalize_data["deal_id"] is not None
        assert finalize_data["deal_status"] == "PENDING_BUYER_APPROVAL"
        assert finalize_data["final_amount"] == "900.00"
        assert finalize_data["commission"] is not None

        deal_id = finalize_data["deal_id"]

        commission = (
            db.query(Commission)
            .filter(Commission.deal_id == deal_id)
            .one()
        )
        commission_id = commission.id

        # ------------------------------------------------------------
        # 9. Buyer accepts final offer.
        # ------------------------------------------------------------
        accept = buyer_client.post(
            f"/api/v1/negotiation/offers/{offer_id}/accept"
        )

        assert accept.status_code == 200, accept.text
        assert accept.json()["deal_status"] == "CONFIRMED"

        db.expire_all()

        confirmed_deal = (
            db.query(Deal)
            .filter(Deal.id == deal_id)
            .one()
        )

        assert confirmed_deal.status == DealStatus.CONFIRMED
        assert confirmed_deal.buyer_approved is True
        assert confirmed_deal.approved_at is not None

        confirmed_commission = (
            db.query(Commission)
            .filter(Commission.id == commission_id)
            .one()
        )
        assert confirmed_commission.status == CommissionStatus.CALCULATED

        # ------------------------------------------------------------
        # 10. Buyer cannot mark the deal as delivered.
        # ------------------------------------------------------------
        buyer_deliver = buyer_client.post(
            f"/deals/{deal_id}/deliver"
        )

        assert buyer_deliver.status_code == 403, buyer_deliver.text

        # ------------------------------------------------------------
        # 11. Merchant marks the confirmed deal as delivered.
        # ------------------------------------------------------------
        deliver = merchant_client.post(
            f"/deals/{deal_id}/deliver"
        )

        assert deliver.status_code == 200, deliver.text

        deliver_data = deliver.json()

        assert deliver_data["id"] == deal_id
        assert deliver_data["status"] == "DELIVERED"
        assert deliver_data["delivered_at"] is not None

        db.expire_all()

        delivered_deal = (
            db.query(Deal)
            .filter(Deal.id == deal_id)
            .one()
        )

        assert delivered_deal.status == DealStatus.DELIVERED
        assert delivered_deal.delivered_at is not None
        assert delivered_deal.received_at is None
        assert delivered_deal.completed_at is None

        delivered_commission = (
            db.query(Commission)
            .filter(Commission.id == commission_id)
            .one()
        )

        # Delivery alone must NOT make the commission DUE.
        assert delivered_commission.status == CommissionStatus.CALCULATED

        # ------------------------------------------------------------
        # 12. Merchant cannot mark the deal as received.
        # ------------------------------------------------------------
        merchant_receive = merchant_client.post(
            f"/deals/{deal_id}/receive"
        )

        assert merchant_receive.status_code == 403, merchant_receive.text

        # ------------------------------------------------------------
        # 13. Commission is already merchant-accepted at creation.
        # ------------------------------------------------------------
        db.expire_all()
        accepted_commission = (
            db.query(Commission)
            .filter(Commission.id == commission_id)
            .one()
        )
        assert accepted_commission.merchant_accepted is True
        assert accepted_commission.status == CommissionStatus.CALCULATED

        # ------------------------------------------------------------
        # 14. Buyer marks the delivered deal as received.
        # ------------------------------------------------------------
        receive = buyer_client.post(
            f"/deals/{deal_id}/receive"
        )

        assert receive.status_code == 200, receive.text

        receive_data = receive.json()

        assert receive_data["id"] == deal_id
        assert receive_data["status"] == "COMPLETED"
        assert receive_data["received_at"] is not None
        assert receive_data["completed_at"] is not None

        # ------------------------------------------------------------
        # 14. Final DB acceptance verification.
        # ------------------------------------------------------------
        db.expire_all()

        completed_deal = (
            db.query(Deal)
            .filter(Deal.id == deal_id)
            .one()
        )

        completed_commission = (
            db.query(Commission)
            .filter(Commission.id == commission_id)
            .one()
        )

        assert completed_deal.status == DealStatus.COMPLETED
        assert completed_deal.buyer_approved is True
        assert completed_deal.delivered_at is not None
        assert completed_deal.received_at is not None
        assert completed_deal.completed_at is not None

        assert completed_commission.status == CommissionStatus.DUE
        assert completed_commission.final_amount is not None
        assert Decimal(
            str(completed_commission.final_amount)
        ) == Decimal("4.50")

        # ------------------------------------------------------------
        # 15. Commission due notification acceptance.
        # ------------------------------------------------------------
        notification = (
            db.query(Notification)
            .filter(
                Notification.event_key
                == f"commission_due:{commission_id}"
            )
            .one()
        )

        assert notification.recipient_user_id == merchant.id
        assert notification.event_type == "COMMISSION_DUE"
        assert notification.related_type == "commission"
        assert notification.related_id == commission_id
        assert notification.status.value == "PENDING"

        assert "4.50" in notification.message
        assert "USD" in notification.message
        assert "تاريخ الاستحقاق" in notification.message
        assert "بيانات التحويل" in notification.message
        assert "رقم الحساب" in notification.message
        assert "اسم الحساب" in notification.message
        assert "تعليمات التحويل" in notification.message
        assert "رقم التحويل" in notification.message
        assert "إثبات التحويل" in notification.message

        notification_count = (
            db.query(Notification)
            .filter(
                Notification.event_key
                == f"commission_due:{commission_id}"
            )
            .count()
        )
        assert notification_count == 1

        # ------------------------------------------------------------
        # 16. Repeated receipt must be rejected.
        # ------------------------------------------------------------
        duplicate_receive = buyer_client.post(
            f"/deals/{deal_id}/receive"
        )

        assert duplicate_receive.status_code == 409, duplicate_receive.text
        assert "only delivered deals can be marked as received" in duplicate_receive.text.lower()

        print("\n===== DEAL DELIVERY / RECEIPT / COMMISSION ACCEPTANCE PASS =====")

    finally:
        # ------------------------------------------------------------
        # 16. Independent cleanup.
        # ------------------------------------------------------------
        try:
            db.rollback()
        except Exception:
            pass

        if commission_id is not None:
            db.query(Commission).filter(
                Commission.id == commission_id
            ).delete(synchronize_session=False)

        if deal_id is not None:
            db.query(DealItem).filter(
                DealItem.deal_id == deal_id
            ).delete(synchronize_session=False)

            db.query(Deal).filter(
                Deal.id == deal_id
            ).delete(synchronize_session=False)

        if offer_id is not None:
            db.query(OfferItem).filter(
                OfferItem.offer_id == offer_id
            ).delete(synchronize_session=False)

            db.query(Notification).filter(
                Notification.related_type == "commission",
                Notification.related_id == commission_id,
            ).delete(synchronize_session=False)

            db.query(Notification).filter(
                Notification.related_type == "offer",
                Notification.related_id == offer_id,
            ).delete(synchronize_session=False)

            db.query(Offer).filter(
                Offer.id == offer_id
            ).delete(synchronize_session=False)

        if room_id is not None:
            db.query(NegotiationParticipant).filter(
                NegotiationParticipant.room_id == room_id
            ).delete(synchronize_session=False)

            db.query(NegotiationRoom).filter(
                NegotiationRoom.id == room_id
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
        # 17. Independent zero-trace verification.
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

        remaining_offers = (
            db.query(Offer)
            .filter(Offer.id == offer_id)
            .count()
            if offer_id is not None
            else 0
        )

        remaining_rooms = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.id == room_id)
            .count()
            if room_id is not None
            else 0
        )

        remaining_deals = (
            db.query(Deal)
            .filter(Deal.id == deal_id)
            .count()
            if deal_id is not None
            else 0
        )

        remaining_commissions = (
            db.query(Commission)
            .filter(Commission.id == commission_id)
            .count()
            if commission_id is not None
            else 0
        )

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
