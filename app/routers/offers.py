from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.notification import NotificationChannel
from app.models.user import UserModel
from app.routers.auth import require_active_subscription, require_role
from app.services.notification_service import NotificationService
from app.services.offer_service import OfferService


router = APIRouter(
    prefix="/api/v1/offers",
    tags=["Offers"],
)


class OfferItemPayload(BaseModel):
    request_item_id: int
    listing_id: int | None = None
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class OfferCreatePayload(BaseModel):
    room_id: int
    currency: str | None = None
    message: str | None = None
    items: list[OfferItemPayload] = Field(min_length=1)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_offer(
    payload: OfferCreatePayload,
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("BUYER")),
    _subscription_user: UserModel = Depends(require_active_subscription),
):
    try:
        offer, room = OfferService.create_buyer_offer(
            db,
            room_id=payload.room_id,
            buyer_id=user.id,
            currency=payload.currency,
            message=payload.message,
            items=[item.model_dump() for item in payload.items],
        )

        NotificationService.create(
            db,
            recipient_user_id=offer.merchant_id,
            event_type="NEW_OFFER",
            title="New buyer offer received",
            message=(
                f"A buyer submitted an offer for your negotiation "
                f"#{room.id}."
            ),
            channel=NotificationChannel.IN_APP,
            related_type="offer",
            related_id=offer.id,
        )

        db.commit()
        db.refresh(offer)
        db.refresh(room)

    except PermissionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception:
        db.rollback()
        raise

    return {
        "id": offer.id,
        "room_id": room.id,
        "request_id": offer.request_id,
        "merchant_id": offer.merchant_id,
        "amount": offer.amount,
        "currency": offer.currency,
        "message": offer.message,
        "status": offer.status,
        "items": [
            {
                "id": item.id,
                "request_item_id": item.request_item_id,
                "listing_id": item.listing_id,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "total_price": str(item.total_price),
            }
            for item in offer.items
        ],
    }
