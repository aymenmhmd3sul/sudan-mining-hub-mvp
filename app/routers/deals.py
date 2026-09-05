from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.deal import Deal
from app.services.deal_service import DealService
from app.models.user import UserModel
from app.routers.auth import get_current_user, require_role

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


@router.post("/{deal_id}/approve")
def approve_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("BUYER")),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    try:
        return DealService.approve_by_buyer(
            db,
            deal,
            user.id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{deal_id}/deliver")
def deliver_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("MERCHANT")),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    try:
        return DealService.mark_delivered(
            db,
            deal,
            user.id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{deal_id}/receive")
def receive_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("BUYER")),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    try:
        return DealService.mark_received(
            db,
            deal,
            user.id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{deal_id}/cancel")
def cancel_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    if user.id not in (deal.buyer_id, deal.merchant_id):
        raise HTTPException(
            status_code=403,
            detail="You are not a participant in this deal",
        )

    try:
        return DealService.cancel(
            db,
            deal,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
