from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.deal import Deal, DealStatus
from app.models.deal_item import DealItem
from app.models.offer_item import OfferItem
from app.models.request_item import RequestItem


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
    def approve_by_buyer(
        db: Session,
        deal: Deal,
    ) -> Deal:
        deal.buyer_approved = True
        deal.status = DealStatus.CONFIRMED

        db.commit()
        db.refresh(deal)

        return deal

    @staticmethod
    def complete_by_buyer(
        db: Session,
        deal: Deal,
    ) -> Deal:
        if not deal.buyer_approved:
            raise ValueError(
                "Buyer approval is required before completing the deal"
            )

        deal.status = DealStatus.COMPLETED

        db.commit()
        db.refresh(deal)

        return deal

    @staticmethod
    def cancel(
        db: Session,
        deal: Deal,
    ) -> Deal:
        if deal.status == DealStatus.COMPLETED:
            raise ValueError(
                "Completed deals cannot be cancelled"
            )

        deal.status = DealStatus.CANCELLED

        db.commit()
        db.refresh(deal)

        return deal
