from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.offer import OfferStatus
from app.models.negotiation import NegotiationParticipant, NegotiationRoom, NegotiationStatus
from app.models.user import UserModel
from app.routers.auth import require_role, require_active_subscription
from app.services.offer_service import OfferService
from app.models.notification import NotificationChannel
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/api/v1/offers", tags=["Offers"])


class OfferItemPayload(BaseModel):
    request_item_id: int
    listing_id: int | None = None
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class OfferCreatePayload(BaseModel):
    request_id: int
    currency: str | None = None
    message: str | None = None
    status: OfferStatus = OfferStatus.SUBMITTED
    items: list[OfferItemPayload] = Field(min_length=1)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_offer(
    payload: OfferCreatePayload,
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("MERCHANT", "ADMIN")),
    _subscription_user: UserModel = Depends(require_active_subscription),
):
    try:
        offer = OfferService.create(
            db,
            request_id=payload.request_id,
            merchant_id=user.id,
            currency=payload.currency,
            message=payload.message,
            status=payload.status,
            items=[item.model_dump() for item in payload.items],
            commit=False,
        )

        room = NegotiationRoom(
            request_id=offer.request_id,
            offer_id=offer.id,
            status=NegotiationStatus.OPEN,
        )
        db.add(room)
        db.flush()

        db.add_all(
            [
                NegotiationParticipant(
                    room_id=room.id,
                    user_id=offer.request.buyer_id,
                ),
                NegotiationParticipant(
                    room_id=room.id,
                    user_id=offer.merchant_id,
                ),
            ]
        )

        NotificationService.create(
            db,
            recipient_user_id=offer.request.buyer_id,
            event_type="NEW_OFFER",
            title="New offer received",
            message=(
                f"A merchant submitted a new offer for your request "
                f"#{offer.request_id}."
            ),
            channel=NotificationChannel.IN_APP,
            related_type="offer",
            related_id=offer.id,
        )

        db.commit()
        db.refresh(offer)
        db.refresh(room)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "id": offer.id,
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
