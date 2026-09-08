from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.offer import Offer, OfferStatus
from app.models.offer_item import OfferItem
from app.models.request_item import RequestItem


class OfferService:
    @staticmethod
    def get_by_id(db: Session, offer_id: int) -> Offer | None:
        return (
            db.query(Offer)
            .filter(Offer.id == offer_id)
            .first()
        )

    @staticmethod
    def list_for_request(
        db: Session,
        request_id: int,
        limit: int = 100,
    ) -> list[Offer]:
        return (
            db.query(Offer)
            .filter(Offer.request_id == request_id)
            .order_by(Offer.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(
        db: Session,
        *,
        items: list[dict] | None = None,
        commit: bool = True,
        **data,
    ) -> Offer:
        items = items or []

        if not items:
            raise ValueError("Offer must contain at least one item")

        request_id = data.get("request_id")
        if request_id is None:
            raise ValueError("request_id is required")

        request_item_ids = [int(item["request_item_id"]) for item in items]
        request_items = (
            db.query(RequestItem)
            .filter(
                RequestItem.id.in_(request_item_ids),
                RequestItem.request_id == request_id,
            )
            .all()
        )
        request_items_by_id = {item.id: item for item in request_items}

        if len(request_items_by_id) != len(set(request_item_ids)):
            raise ValueError(
                "Every OfferItem must reference a RequestItem belonging to the request"
            )

        offer_items = []
        grand_total = Decimal("0.00")

        try:
            for payload in items:
                quantity = int(payload["quantity"])
                unit_price = Decimal(str(payload["unit_price"]))

                if quantity <= 0:
                    raise ValueError("OfferItem quantity must be greater than zero")
                if unit_price < 0:
                    raise ValueError("OfferItem unit_price cannot be negative")

                total_price = (
                    unit_price * Decimal(quantity)
                ).quantize(Decimal("0.01"))

                offer_items.append(
                    OfferItem(
                        request_item_id=int(payload["request_item_id"]),
                        listing_id=payload.get("listing_id"),
                        quantity=quantity,
                        unit_price=unit_price,
                        total_price=total_price,
                    )
                )
                grand_total += total_price

        except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
            raise ValueError(f"Invalid OfferItem payload: {exc}") from exc

        data["amount"] = str(grand_total.quantize(Decimal("0.01")))

        offer = Offer(**data)
        offer.items = offer_items

        db.add(offer)

        if commit:
            try:
                db.commit()
                db.refresh(offer)
            except Exception:
                db.rollback()
                raise
        else:
            db.flush()

        return offer
