from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.deal import Deal
from app.models.user import UserModel
from app.routers.auth import get_current_user

router = APIRouter(prefix="/deals", tags=["Deals"])


@router.get("/{deal_id}")
def get_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    if not deal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    if user.id not in (deal.buyer_id, deal.merchant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant in this deal",
        )

    return deal
