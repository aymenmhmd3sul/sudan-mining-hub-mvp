from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.deal import Deal, DealStatus
from app.models.user import UserModel, UserRole
from app.models.deal_item import DealItem
from app.models.offer_item import OfferItem
from app.models.request_item import RequestItem
from app.services.commission_service import CommissionService


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

        db.commit()
        db.refresh(deal)
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
    ) -> Deal:
        if deal.buyer_id != buyer_id:
            raise PermissionError("Only the buyer can approve the deal")
        if deal.status != DealStatus.PENDING_BUYER_APPROVAL:
            raise ValueError(
                "Only deals pending buyer approval can be approved"
            )
        if deal.buyer_approved:
            raise ValueError("Deal has already been approved by the buyer")

        from datetime import datetime, timezone

        try:
            settings = CommissionService.get_active_settings(
                db,
                deal.currency,
            )

            final_commission, adjusted_by_platform = (
                CommissionService.calculate_platform_commission(
                    deal_amount=Decimal(str(deal.final_amount)),
                    merchant_amount=None,
                    merchant_rate=None,
                    minimum_amount=settings.minimum_amount,
                    platform_rate=settings.commission_rate,
                    currency=deal.currency,
                )
            )

            platform_amount = (
                Decimal(str(deal.final_amount))
                * settings.commission_rate
                / Decimal("100")
            )

            CommissionService.create(
                db,
                deal_id=deal.id,
                merchant_id=deal.merchant_id,
                proposed_amount=None,
                proposed_currency=None,
                proposed_rate=None,
                platform_amount=platform_amount,
                platform_rate=settings.commission_rate,
                minimum_amount=settings.minimum_amount,
                final_amount=final_commission,
                currency=deal.currency,
                adjusted_by_platform=adjusted_by_platform,
            )

            deal.buyer_approved = True
            deal.status = DealStatus.CONFIRMED
            deal.approved_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(deal)
            return deal

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def mark_delivered(
        db: Session,
        deal: Deal,
        merchant_id: int,
    ) -> Deal:
        if deal.merchant_id != merchant_id:
            raise PermissionError("Only the merchant can mark the deal as delivered")

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

        from datetime import datetime, timezone

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
