from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.deal import Deal, DealStatus
from app.models.listing import Listing, ListingStatus
from app.models.user import UserModel, UserRole
from app.models.deal_item import DealItem
from app.models.negotiation import NegotiationRoom, NegotiationStatus
from app.models.offer import Offer, OfferStatus
from app.models.offer_item import OfferItem
from app.models.request_item import RequestItem
from app.services.commission_service import CommissionService
from app.services.commission_payment_settings_service import (
    CommissionPaymentSettingsService,
)
from app.services.notification_service import NotificationService
from app.models.notification import NotificationChannel


class DealService:

    @staticmethod
    def get_by_id(
        db: Session,
        deal_id: int,
    ) -> Deal | None:
        return (
            db.query(Deal)
            .filter(Deal.id == deal_id)
            .first()
        )

    @staticmethod
    def get_for_agent(
        db: Session,
        agent_id: int,
    ) -> list[Deal]:
        return (
            db.query(Deal)
            .filter(Deal.agent_id == agent_id)
            .order_by(Deal.id.desc())
            .all()
        )

    @staticmethod
    def create(
        db: Session,
        *,
        request_id: int,
        offer_id: int,
        listing_id: int | None,
        negotiation_room_id: int,
        buyer_id: int,
        merchant_id: int,
        final_amount: Decimal,
        currency: str,
        commit: bool = True,
    ) -> Deal:
        deal = Deal(
            request_id=request_id,
            offer_id=offer_id,
            listing_id=listing_id,
            negotiation_room_id=negotiation_room_id,
            buyer_id=buyer_id,
            merchant_id=merchant_id,
            final_amount=final_amount,
            currency=currency,
            status=DealStatus.PENDING_BUYER_APPROVAL,
            buyer_approved=False,
        )

        db.add(deal)
        db.flush()

        offer_items = (
            db.query(OfferItem)
            .filter(OfferItem.offer_id == offer_id)
            .order_by(OfferItem.id.asc())
            .all()
        )

        for offer_item in offer_items:
            request_item = (
                db.query(RequestItem)
                .filter(RequestItem.id == offer_item.request_item_id)
                .first()
            )
            if request_item is None:
                raise ValueError(
                    f"Request item not found for offer item {offer_item.id}"
                )

            db.add(
                DealItem(
                    deal_id=deal.id,
                    request_item_id=offer_item.request_item_id,
                    listing_id=offer_item.listing_id,
                    title=request_item.title,
                    quantity=offer_item.quantity,
                    unit_price=offer_item.unit_price,
                    total_price=offer_item.total_price,
                )
            )

        if commit:
            db.commit()
            db.refresh(deal)
        else:
            db.flush()

        return deal

    @staticmethod
    def assign_agent(
        db: Session,
        deal: Deal,
        agent_id: int,
    ) -> Deal:
        agent = (
            db.query(UserModel)
            .filter(UserModel.id == agent_id)
            .first()
        )
        if agent is None:
            raise ValueError("Agent not found")

        if agent.role != UserRole.AGENT:
            raise ValueError("Selected user is not an agent")

        if deal.status in (
            DealStatus.COMPLETED,
            DealStatus.CANCELLED,
        ):
            raise ValueError("Cannot assign agent to a closed deal")

        deal.agent_id = agent.id
        db.commit()
        db.refresh(deal)
        return deal

    @staticmethod
    def approve_by_buyer(
        db: Session,
        deal: Deal,
        buyer_id: int,
        commit: bool = True,
    ) -> Deal:
        locked_deal = (
            db.query(Deal)
            .filter(Deal.id == deal.id)
            .with_for_update()
            .first()
        )
        if locked_deal is None:
            raise ValueError("Deal not found")

        if locked_deal.buyer_id != buyer_id:
            raise PermissionError("Only the buyer can approve the deal")

        # A retry by the same buyer is a no-op and cannot repeat confirmation
        # effects or create another commission.
        if (
            locked_deal.status == DealStatus.CONFIRMED
            and locked_deal.buyer_approved
        ):
            return locked_deal

        if locked_deal.status != DealStatus.PENDING_BUYER_APPROVAL:
            raise ValueError(
                "Only deals pending buyer approval can be approved"
            )
        if locked_deal.buyer_approved:
            raise ValueError("Deal approval state is inconsistent")

        request = (
            db.query(BuyerRequest)
            .filter(BuyerRequest.id == locked_deal.request_id)
            .first()
        )
        offer = (
            db.query(Offer)
            .filter(Offer.id == locked_deal.offer_id)
            .with_for_update()
            .first()
        )
        room = (
            db.query(NegotiationRoom)
            .filter(NegotiationRoom.id == locked_deal.negotiation_room_id)
            .with_for_update()
            .first()
        )
        if request is None or offer is None or room is None:
            raise ValueError("Deal relationships are incomplete")

        if (
            request.buyer_id != locked_deal.buyer_id
            or offer.request_id != request.id
            or offer.merchant_id != locked_deal.merchant_id
            or offer.listing_id != locked_deal.listing_id
            or room.request_id != request.id
            or (room.offer_id is not None and room.offer_id != offer.id)
            or (
                request.listing_id is not None
                and request.listing_id != locked_deal.listing_id
            )
        ):
            raise ValueError("Deal relationships do not match")

        listing = None
        if locked_deal.listing_id is not None:
            listing = (
                db.query(Listing)
                .filter(Listing.id == locked_deal.listing_id)
                .with_for_update()
                .first()
            )
            if listing is None:
                raise ValueError("Listing not found")
            if listing.owner_id != locked_deal.merchant_id:
                raise PermissionError(
                    "Deal merchant does not own the linked listing"
                )

        commission = CommissionService.get_for_deal(db, locked_deal.id)
        if commission is None:
            raise ValueError(
                "Commission must be calculated before buyer approval"
            )

        if offer.status not in (OfferStatus.FINAL, OfferStatus.ACCEPTED):
            raise ValueError("Offer is not ready for buyer approval")
        if room.status not in (NegotiationStatus.AGREED, NegotiationStatus.CLOSED):
            raise ValueError("Negotiation is not awaiting buyer approval")

        locked_deal.buyer_approved = True
        locked_deal.status = DealStatus.CONFIRMED
        locked_deal.approved_at = datetime.now(timezone.utc)
        offer.status = OfferStatus.ACCEPTED
        room.status = NegotiationStatus.CLOSED
        request.status = RequestStatus.NEGOTIATING

        if listing is not None and listing.status != ListingStatus.SOLD:
            listing.status = ListingStatus.SOLD
            listing.version += 1
            other_offers = (
                db.query(Offer)
                .filter(
                    Offer.listing_id == listing.id,
                    Offer.id != offer.id,
                    Offer.status.in_((OfferStatus.SUBMITTED, OfferStatus.FINAL)),
                )
                .all()
            )
            for other_offer in other_offers:
                other_offer.status = OfferStatus.CLOSED
                other_rooms = (
                    db.query(NegotiationRoom)
                    .filter(
                        NegotiationRoom.offer_id == other_offer.id,
                        NegotiationRoom.status.in_(
                            (NegotiationStatus.OPEN, NegotiationStatus.AGREED)
                        ),
                    )
                    .all()
                )
                for other_room in other_rooms:
                    other_room.status = NegotiationStatus.CLOSED

        try:
            if commit:
                db.commit()
                db.refresh(locked_deal)
            else:
                db.flush()
        except Exception:
            if commit:
                db.rollback()
            raise

        return locked_deal

    @staticmethod
    def mark_delivered(
        db: Session,
        deal: Deal,
        actor_id: int,
    ) -> Deal:
        if actor_id not in (deal.merchant_id, deal.agent_id):
            raise PermissionError(
                "Only the merchant or assigned agent can mark the deal as delivered"
            )

        if deal.status != DealStatus.CONFIRMED:
            raise ValueError("Only CONFIRMED deals can be marked as delivered")

        if deal.delivered_at is not None:
            raise ValueError("Deal has already been delivered")

        from datetime import datetime, timezone

        deal.status = DealStatus.DELIVERED
        deal.delivered_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(deal)

        return deal

    @staticmethod
    def mark_received(
        db: Session,
        deal: Deal,
        buyer_id: int,
    ) -> Deal:
        if deal.buyer_id != buyer_id:
            raise PermissionError("Only the buyer can mark the deal as received")

        if deal.status != DealStatus.DELIVERED:
            raise ValueError("Only DELIVERED deals can be marked as received")

        if deal.received_at is not None:
            raise ValueError("Deal has already been marked as received")

        commission = CommissionService.get_for_deal(db, deal.id)
        if commission is not None:
            CommissionService.mark_due(db, commission)

            payment_settings = CommissionPaymentSettingsService.get_active(
                db,
                commission.currency,
            )

            if payment_settings is not None:
                payment_details = (
                    f"رقم الحساب: "
                    f"{payment_settings.account_number or 'غير مُعد بعد'}\n"
                    f"اسم الحساب: "
                    f"{payment_settings.account_name or 'غير مُعد بعد'}\n"
                    f"تعليمات التحويل: "
                    f"{payment_settings.payment_instructions or 'غير مُعدّة بعد'}"
                )
            else:
                payment_details = (
                    "بيانات التحويل لهذه العملة غير مُعدّة بعد. "
                    "يرجى التواصل مع المشرف."
                )

            NotificationService.create(
                db,
                recipient_user_id=deal.merchant_id,
                event_type="COMMISSION_DUE",
                event_key=f"commission_due:{commission.id}",
                title="العمولة مستحقة بعد استلام الصفقة",
                message=(
                    f"تم استلام الصفقة رقم #{deal.id} من المشتري.\n\n"
                    f"مبلغ العمولة المستحق: "
                    f"{commission.final_amount} {commission.currency}\n"
                    f"تاريخ الاستحقاق: "
                    f"{datetime.now(timezone.utc).date().isoformat()}\n\n"
                    f"بيانات التحويل:\n"
                    f"{payment_details}\n\n"
                    "بعد تنفيذ التحويل، يجب تسجيل تاريخ التحويل "
                    "ورقم التحويل وإرفاق إثبات التحويل."
                ),
                channel=NotificationChannel.IN_APP,
                related_type="commission",
                related_id=commission.id,
            )

        now = datetime.now(timezone.utc)
        deal.status = DealStatus.COMPLETED
        deal.received_at = now
        deal.completed_at = now

        db.commit()
        db.refresh(deal)

        return deal

    @staticmethod
    def complete_by_buyer(
        db: Session,
        deal: Deal,
    ) -> Deal:
        raise ValueError(
            "Direct completion is disabled; buyer receipt is required"
        )

    @staticmethod
    def cancel(
        db: Session,
        deal: Deal,
    ) -> Deal:
        if deal.status == DealStatus.COMPLETED:
            raise ValueError(
                "Completed deals cannot be cancelled"
            )

        commission = CommissionService.get_for_deal(db, deal.id)
        if commission is not None:
            CommissionService.waive(db, commission)

        deal.status = DealStatus.CANCELLED

        db.commit()
        db.refresh(deal)

        return deal
