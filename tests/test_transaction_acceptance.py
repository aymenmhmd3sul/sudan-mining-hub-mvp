import uuid
from decimal import Decimal

import pytest

import app.db.base  # noqa: F401 — load the central ORM registry first

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.user import UserModel, UserRole
from app.models.listing_category import ListingCategory
from app.models.listing import Listing, ListingStatus, ListingType, QuantityMode
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
from app.models.commission import Commission, CommissionStatus
from app.services.offer_service import OfferService
from app.services.negotiation_service import NegotiationService


def test_full_transaction_acceptance_isolation():
    marker = f"TX_ACCEPTANCE_{uuid.uuid4().hex}"

    db = SessionLocal()

    buyer = None
    merchant = None
    category = None
    listing = None
    request = None
    request_item = None
    offer = None
    room = None
    participant = None
    deal = None
    commission = None

    try:
        # ------------------------------------------------------------
        # 1. Create isolated users.
        # ------------------------------------------------------------
        password_hash = get_password_hash("transaction-acceptance-test")

        buyer = UserModel(
            email=f"{marker.lower()}_buyer@example.invalid",
            hashed_password=password_hash,
            full_name=f"{marker} Buyer",
            role=UserRole.BUYER,
            is_approved=True,
            email_verified=True,
        )

        merchant = UserModel(
            email=f"{marker.lower()}_merchant@example.invalid",
            hashed_password=password_hash,
            full_name=f"{marker} Merchant",
            role=UserRole.MERCHANT,
            is_approved=True,
            email_verified=True,
        )

        db.add_all([buyer, merchant])
        db.flush()

        # ------------------------------------------------------------
        # 2. Create an isolated category and active listing.
        # ------------------------------------------------------------
        category = ListingCategory(
            name=f"{marker} Category",
            status="ACTIVE",
            description=f"{marker} acceptance-test category",
        )
        db.add(category)
        db.flush()

        listing = Listing(
            owner_id=merchant.id,
            category_id=category.category_id,
            title=f"{marker} Listing",
            description=f"{marker} acceptance-test listing",
            listing_type=ListingType.ASSET,
            quantity_mode=QuantityMode.SINGLE,
            price=1000.0,
            currency="USD",
            is_negotiable=True,
            status=ListingStatus.ACTIVE,
            version=1,
        )
        db.add(listing)
        db.flush()

        # ------------------------------------------------------------
        # 3. Create buyer request + request item.
        # ------------------------------------------------------------
        request = BuyerRequest(
            buyer_id=buyer.id,
            listing_id=listing.id,
            title=f"{marker} Buyer Request",
            description=f"{marker} acceptance-test request",
            status=RequestStatus.OPEN,
            currency="USD",
        )
        db.add(request)
        db.flush()

        request_item = RequestItem(
            request_id=request.id,
            category_id=category.category_id,
            title=f"{marker} Requested Item",
            description=f"{marker} acceptance-test request item",
            quantity=1,
            unit="unit",
        )
        db.add(request_item)
        db.flush()

        # ------------------------------------------------------------
        # 4. Create offer through the real OfferService.
        # ------------------------------------------------------------
        offer = OfferService.create(
            db,
            request_id=request.id,
            merchant_id=merchant.id,
            listing_id=listing.id,
            currency="USD",
            message=f"{marker} offer",
            status=OfferStatus.SUBMITTED,
            items=[
                {
                    "request_item_id": request_item.id,
                    "listing_id": listing.id,
                    "quantity": 1,
                    "unit_price": Decimal("900.00"),
                }
            ],
            commit=False,
        )
        db.flush()

        assert offer.id is not None
        assert offer.amount == "900.00"

        # ------------------------------------------------------------
        # 5. Create negotiation room + both participants.
        # ------------------------------------------------------------
        room = NegotiationRoom(
            request_id=request.id,
            offer_id=offer.id,
            status=NegotiationStatus.OPEN,
        )
        db.add(room)
        db.flush()

        merchant_participant = NegotiationParticipant(
            room_id=room.id,
            user_id=merchant.id,
        )
        participant = NegotiationParticipant(
            room_id=room.id,
            user_id=buyer.id,
        )
        db.add_all([merchant_participant, participant])
        db.flush()

        # The current workflow requires merchant approval of the negotiation
        # before the merchant can finalize its offer.
        NegotiationService.approve_negotiation(
            db,
            room_id=room.id,
            merchant_id=merchant.id,
        )

        # ------------------------------------------------------------
        # 6. Merchant finalizes offer.
        #    This must create the Deal + Commission through production
        #    services and transition the request/room/offer correctly.
        # ------------------------------------------------------------
        finalized_room = NegotiationService.finalize_offer(
            db,
            offer_id=offer.id,
            merchant_id=merchant.id,
        )

        db.refresh(offer)
        db.refresh(request)
        db.refresh(room)

        deal = (
            db.query(Deal)
            .filter(Deal.offer_id == offer.id)
            .one()
        )

        commission = (
            db.query(Commission)
            .filter(Commission.deal_id == deal.id)
            .one()
        )

        assert finalized_room.id == room.id
        assert offer.status == OfferStatus.FINAL
        assert room.status == NegotiationStatus.AGREED
        assert request.status == RequestStatus.NEGOTIATING

        assert deal.status == DealStatus.PENDING_BUYER_APPROVAL
        assert deal.buyer_id == buyer.id
        assert deal.merchant_id == merchant.id
        assert deal.final_amount == Decimal("900.00")

        assert commission.deal_id == deal.id
        assert commission.merchant_id == merchant.id
        assert commission.status == CommissionStatus.CALCULATED
        assert commission.merchant_accepted is True

        # ------------------------------------------------------------
        # 7. Buyer accepts the final offer through the real service.
        # ------------------------------------------------------------
        accepted_room = NegotiationService.accept_offer(
            db,
            offer_id=offer.id,
            buyer_id=buyer.id,
        )

        db.refresh(offer)
        db.refresh(room)
        db.refresh(request)
        db.refresh(deal)
        db.refresh(commission)
        db.refresh(listing)

        assert accepted_room.id == room.id
        assert offer.status == OfferStatus.ACCEPTED
        assert room.status == NegotiationStatus.CLOSED
        assert request.status == RequestStatus.NEGOTIATING

        assert deal.status == DealStatus.CONFIRMED
        assert deal.buyer_approved is True
        assert deal.buyer_id == buyer.id
        assert deal.merchant_id == merchant.id

        assert commission.status == CommissionStatus.CALCULATED
        assert commission.merchant_accepted is True

        assert listing.status == ListingStatus.SOLD
        assert listing.version == 2

        print("===== FULL TRANSACTION ACCEPTANCE PASS =====")

    finally:
        # ------------------------------------------------------------
        # Snapshot scalar IDs BEFORE ORM instances are deleted.
        # Never access deleted ORM instances during verification.
        # ------------------------------------------------------------
        db.rollback()

        room_id = room.id if room is not None else None
        deal_id = deal.id if deal is not None else None
        commission_id = commission.id if commission is not None else None
        offer_id = offer.id if offer is not None else None
        request_item_id = request_item.id if request_item is not None else None
        request_id = request.id if request is not None else None
        listing_id = listing.id if listing is not None else None
        category_id = category.category_id if category is not None else None
        merchant_id = merchant.id if merchant is not None else None
        buyer_id = buyer.id if buyer is not None else None

        # ------------------------------------------------------------
        # Cleanup in FK-safe order.
        # ------------------------------------------------------------
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

        if listing_id is not None:
            db.query(Listing).filter(
                Listing.id == listing_id
            ).delete(synchronize_session=False)

        if category_id is not None:
            db.query(ListingCategory).filter(
                ListingCategory.category_id == category_id
            ).delete(synchronize_session=False)

        if merchant_id is not None:
            db.query(UserModel).filter(
                UserModel.id == merchant_id
            ).delete(synchronize_session=False)

        if buyer_id is not None:
            db.query(UserModel).filter(
                UserModel.id == buyer_id
            ).delete(synchronize_session=False)

        db.commit()

        # ------------------------------------------------------------
        # Independent cleanup verification using scalar IDs only.
        # ------------------------------------------------------------
        remaining_users = (
            db.query(UserModel)
            .filter(UserModel.email.like(f"{marker.lower()}_%"))
            .count()
        )

        remaining_categories = (
            db.query(ListingCategory)
            .filter(ListingCategory.name.like(f"{marker}%"))
            .count()
        )

        remaining_listings = (
            db.query(Listing)
            .filter(Listing.title.like(f"{marker}%"))
            .count()
        )

        remaining_requests = (
            db.query(BuyerRequest)
            .filter(BuyerRequest.title.like(f"{marker}%"))
            .count()
        )

        remaining_offers = (
            db.query(Offer)
            .filter(Offer.message == f"{marker} offer")
            .count()
        )

        remaining_rooms = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.id == room_id)
            .count()
            if room_id is not None else 0
        )

        remaining_deals = (
            db.query(Deal)
            .filter(Deal.id == deal_id)
            .count()
            if deal_id is not None else 0
        )

        remaining_commissions = (
            db.query(Commission)
            .filter(Commission.id == commission_id)
            .count()
            if commission_id is not None else 0
        )

        assert remaining_users == 0
        assert remaining_categories == 0
        assert remaining_listings == 0
        assert remaining_requests == 0
        assert remaining_offers == 0
        assert remaining_rooms == 0
        assert remaining_deals == 0
        assert remaining_commissions == 0

        print("===== CLEANUP VERIFICATION PASS =====")
        print("TEST USERS REMAINING:", remaining_users)
        print("TEST CATEGORIES REMAINING:", remaining_categories)
        print("TEST LISTINGS REMAINING:", remaining_listings)
        print("TEST REQUESTS REMAINING:", remaining_requests)
        print("TEST OFFERS REMAINING:", remaining_offers)
        print("TEST ROOMS REMAINING:", remaining_rooms)
        print("TEST DEALS REMAINING:", remaining_deals)
        print("TEST COMMISSIONS REMAINING:", remaining_commissions)

        db.close()
