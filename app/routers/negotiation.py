from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import UserModel
from app.routers.auth import require_active_subscription, require_role
from app.services.negotiation_service import NegotiationService


router = APIRouter(
    prefix="/api/v1/negotiation",
    tags=["Negotiation"],
)


@router.post("/{room_id}/approve")
def approve_negotiation(
    room_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("MERCHANT")),
    _subscription_user: UserModel = Depends(require_active_subscription),
):
    try:
        room = NegotiationService.approve_negotiation(
            db,
            room_id=room_id,
            merchant_id=user.id,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "room_id": room.id,
        "request_id": room.request_id,
        "status": room.status,
        "merchant_approved_at": room.merchant_approved_at,
    }
