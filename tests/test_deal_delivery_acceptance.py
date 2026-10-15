import uuid
from decimal import Decimal

import app.db.base  # noqa: F401
from fastapi.testclient import TestClient

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.main import app
from app.models.user import UserModel, UserRole
from app.models.listing_category import ListingCategory
from app.models.listing import Listing, ListingStatus, ListingType, QuantityMode
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
from app.models.commission_payment_settings import CommissionPaymentSettings
from app.services.subscription_service import SubscriptionService
from app.services.notification_service import NotificationService


def test_deal_delivery_receipt_commission_http_acceptance_isolation(monkeypatch):
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
    payment_settings_id = None

    try:
        # Use temporary USD settings only when no active settings exist.
        active_usd = (
            db.query(CommissionPaymentSettings)
            .filter(
                CommissionPaymentSettings.currency == "USD",
                CommissionPaymentSettings.is_active.is_(True),
            )
            .first()
        )
        if active_usd is not None:
            assert active_usd.account_number
            assert active_usd.account_name
            assert active_usd.payment_instructions
        else:
            temporary_settings = CommissionPaymentSettings(
                currency="USD",
                account_number="TEST-USD-ACCOUNT",
                account_name="Temporary Test Account",
                payment_instructions="Temporary USD test instructions",
                is_active=True,
            )
            db.add(temporary_settings)
            db.commit()
            payment_settings_id = temporary_settings.id
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
            quantity_mode=QuantityMode.BULK,
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
        push_calls = []

        def failing_web_push(db, **kwargs):
            push_calls.append(kwargs)
            raise RuntimeError("Simulated Web Push delivery failure")

        monkeypatch.setattr(
            NotificationService,
            "send_web_push",
            staticmethod(failing_web_push),
        )

        receive = buyer_client.post(
            f"/deals/{deal_id}/receive"
        )

        assert len(push_calls) == 1
        assert push_calls[0]["recipient_user_id"] == merchant.id
        assert push_calls[0]["title"] == "العمولة مستحقة بعد استلام الصفقة"
        assert push_calls[0]["url"] == "/merchant/"

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

        # Recover test-owned request and child IDs after an early failure.
        if request_id is None and buyer is not None:
            request_id = (
                db.query(BuyerRequest.id)
                .filter(
                    BuyerRequest.buyer_id == buyer.id,
                    BuyerRequest.title == f"{marker} Listing",
                )
                .order_by(BuyerRequest.id.desc())
                .scalar()
            )

        if request_id is not None and request_item_id is None:
            request_item_id = (
                db.query(RequestItem.id)
                .filter(RequestItem.request_id == request_id)
                .order_by(RequestItem.id.desc())
                .scalar()
            )

        if request_id is not None and room_id is None:
            room_id = (
                db.query(NegotiationRoom.id)
                .filter(NegotiationRoom.request_id == request_id)
                .order_by(NegotiationRoom.id.desc())
                .scalar()
            )

        # Recover a persisted offer if the test failed before capturing its ID.
        if offer_id is None and request_id is not None:
            offer_id = (
                db.query(Offer.id)
                .filter(Offer.request_id == request_id)
                .order_by(Offer.id.desc())
                .scalar()
            )

        if offer_id is None and room_id is not None:
            offer_id = (
                db.query(NegotiationRoom.offer_id)
                .filter(
                    NegotiationRoom.id == room_id,
                    NegotiationRoom.offer_id.is_not(None),
                )
                .scalar()
            )

        if payment_settings_id is not None:
            db.query(CommissionPaymentSettings).filter(
                CommissionPaymentSettings.id == payment_settings_id,
                CommissionPaymentSettings.currency == "USD",
            ).delete(synchronize_session=False)
            db.flush()

        # Recover the test deal even if the main flow did not capture its ID.
        cleanup_deal_id = deal_id
        if cleanup_deal_id is None and offer_id is not None:
            cleanup_deal_id = (
                db.query(Deal.id)
                .filter(Deal.offer_id == offer_id)
                .scalar()
            )
        if cleanup_deal_id is None and request_id is not None:
            cleanup_deal_id = (
                db.query(Deal.id)
                .filter(Deal.request_id == request_id)
                .scalar()
            )

        # Save commission IDs before deleting commission rows.
        commission_ids_for_cleanup = []
        if cleanup_deal_id is not None:
            commission_ids_for_cleanup = [
                row[0]
                for row in db.query(Commission.id).filter(
                    Commission.deal_id == cleanup_deal_id
                ).all()
            ]
        if commission_id is not None and commission_id not in commission_ids_for_cleanup:
            commission_ids_for_cleanup.append(commission_id)

        if commission_ids_for_cleanup:
            db.query(Notification).filter(
                Notification.related_type == "commission",
                Notification.related_id.in_(commission_ids_for_cleanup),
            ).delete(synchronize_session=False)

            db.query(Notification).filter(
                Notification.event_key.in_([
                    f"commission_due:{cid}"
                    for cid in commission_ids_for_cleanup
                ])
            ).delete(synchronize_session=False)

        if cleanup_deal_id is not None:
            db.query(Commission).filter(
                Commission.deal_id == cleanup_deal_id
            ).delete(synchronize_session=False)
            db.flush()
        elif commission_id is not None:
            db.query(Notification).filter(
                Notification.event_key == f"commission_due:{commission_id}"
            ).delete(synchronize_session=False)
            db.query(Commission).filter(
                Commission.id == commission_id
            ).delete(synchronize_session=False)

        if cleanup_deal_id is not None:
            db.query(DealItem).filter(
                DealItem.deal_id == cleanup_deal_id
            ).delete(synchronize_session=False)

            db.query(Deal).filter(
                Deal.id == cleanup_deal_id
            ).delete(synchronize_session=False)

        if offer_id is not None:
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

        if room_id is not None:
            db.query(NegotiationParticipant).filter(
                NegotiationParticipant.room_id == room_id
            ).delete(synchronize_session=False)

            db.query(NegotiationRoom).filter(
                NegotiationRoom.id == room_id
            ).delete(synchronize_session=False)

        if request_id is not None:
            db.query(RequestItem).filter(
                RequestItem.request_id == request_id
            ).delete(synchronize_session=False)
        elif request_item_id is not None:
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

        # Verify child rows and subscriptions belonging to this test run.
        remaining_deal_items = (
            db.query(DealItem)
            .filter(DealItem.deal_id == cleanup_deal_id)
            .count()
            if cleanup_deal_id is not None
            else 0
        )

        remaining_offer_items = (
            db.query(OfferItem)
            .filter(OfferItem.offer_id == offer_id)
            .count()
            if offer_id is not None
            else 0
        )

        remaining_request_items = (
            db.query(RequestItem)
            .filter(RequestItem.request_id == request_id)
            .count()
            if request_id is not None
            else (
                db.query(RequestItem)
                .filter(RequestItem.id == request_item_id)
                .count()
                if request_item_id is not None
                else 0
            )
        )

        remaining_subscriptions = (
            db.query(Subscription)
            .filter(
                Subscription.plan.in_([
                    f"{marker}-buyer",
                    f"{marker}-merchant",
                ])
            )
            .count()
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
            .filter(Deal.id == cleanup_deal_id)
            .count()
            if cleanup_deal_id is not None
            else 0
        )

        remaining_commissions = 0
        if cleanup_deal_id is not None:
            remaining_commissions = (
                db.query(Commission)
                .filter(Commission.deal_id == cleanup_deal_id)
                .count()
            )
        elif commission_ids_for_cleanup:
            remaining_commissions = (
                db.query(Commission)
                .filter(Commission.id.in_(commission_ids_for_cleanup))
                .count()
            )

        remaining_commission_notifications = 0
        if commission_ids_for_cleanup:
            remaining_commission_notifications += (
                db.query(Notification)
                .filter(
                    Notification.related_type == "commission",
                    Notification.related_id.in_(commission_ids_for_cleanup),
                )
                .count()
            )
            remaining_commission_notifications += (
                db.query(Notification)
                .filter(
                    Notification.event_key.in_([
                        f"commission_due:{cid}"
                        for cid in commission_ids_for_cleanup
                    ])
                )
                .count()
            )

        remaining_payment_settings = (
            db.query(CommissionPaymentSettings)
            .filter(
                CommissionPaymentSettings.id == payment_settings_id,
                CommissionPaymentSettings.currency == "USD",
                CommissionPaymentSettings.account_number == "TEST-USD-ACCOUNT",
                CommissionPaymentSettings.account_name == "Temporary Test Account",
            )
            .count()
            if payment_settings_id is not None
            else 0
        )
        print("===== CLEANUP VERIFICATION =====")
        print("TEST USERS REMAINING:", remaining_users)
        print("TEST CATEGORIES REMAINING:", remaining_categories)
        print("TEST LISTINGS REMAINING:", remaining_listings)
        print("TEST REQUESTS REMAINING:", remaining_requests)
        print("TEST DEAL ITEMS REMAINING:", remaining_deal_items)
        print("TEST OFFER ITEMS REMAINING:", remaining_offer_items)
        print("TEST REQUEST ITEMS REMAINING:", remaining_request_items)
        print("TEST SUBSCRIPTIONS REMAINING:", remaining_subscriptions)
        print("TEST OFFERS REMAINING:", remaining_offers)
        print("TEST ROOMS REMAINING:", remaining_rooms)
        print("TEST DEALS REMAINING:", remaining_deals)
        print("TEST COMMISSIONS REMAINING:", remaining_commissions)
        print("TEST COMMISSION NOTIFICATIONS REMAINING:", remaining_commission_notifications)
        print("TEMP PAYMENT SETTINGS REMAINING:", remaining_payment_settings)

        assert remaining_users == 0
        assert remaining_categories == 0
        assert remaining_listings == 0
        assert remaining_requests == 0
        assert remaining_deal_items == 0
        assert remaining_offer_items == 0
        assert remaining_request_items == 0
        assert remaining_subscriptions == 0
        assert remaining_offers == 0
        assert remaining_rooms == 0
        assert remaining_deals == 0
        assert remaining_commissions == 0
        assert remaining_commission_notifications == 0
        assert remaining_payment_settings == 0

        db.close()
