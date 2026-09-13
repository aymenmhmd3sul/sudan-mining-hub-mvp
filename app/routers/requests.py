from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import UserModel
from app.routers.auth import require_role
from app.services.request_service import RequestService

router = APIRouter(
    prefix="/api/v1/requests",
    tags=["Requests"],
)


@router.get("")
def list_requests(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("MERCHANT", "ADMIN")),
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
