from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import UserModel, UserRole
from app.routers.auth import (
    get_current_user,
    require_role,
    require_seller_role,
)
from app.services.request_service import RequestService
from app.services.subscription_service import SubscriptionService


def require_agent_active_subscription(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    if (
        user.role == UserRole.AGENT
        and not SubscriptionService.is_active(db, user.id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required",
        )
    return user

router = APIRouter(
    prefix="/api/v1/requests",
    tags=["Requests"],
)


@router.get("/mine")
def list_my_requests(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("BUYER", "AGENT")),
):
    requests = RequestService.list_for_buyer(
        db,
        buyer_id=user.id,
        limit=limit,
    )

    return [
        {
            "id": request.id,
            "buyer_id": request.buyer_id,
            "listing_id": request.listing_id,
            "title": request.title,
            "description": request.description,
            "status": request.status,
            "currency": request.currency,
            "target_location": request.target_location,
            "created_at": request.created_at,
            "updated_at": request.updated_at,
            "items": [
                {
                    "id": item.id,
                    "category_id": item.category_id,
                    "title": item.title,
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit": item.unit,
                }
                for item in request.items
            ],
        }
        for request in requests
    ]


@router.get("")
def list_requests(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_seller_role("MERCHANT", "AGENT", "ADMIN")),
    _agent_subscription_user: UserModel = Depends(require_agent_active_subscription),
):
    requests = RequestService.list_open(db, limit=limit)

    return [
        {
            "id": request.id,
            "buyer_id": request.buyer_id,
            "listing_id": request.listing_id,
            "title": request.title,
            "description": request.description,
            "status": request.status,
            "currency": request.currency,
            "target_location": request.target_location,
            "created_at": request.created_at,
            "updated_at": request.updated_at,
            "items": [
                {
                    "id": item.id,
                    "category_id": item.category_id,
                    "title": item.title,
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit": item.unit,
                }
                for item in request.items
            ],
        }
        for request in requests
    ]
