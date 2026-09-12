from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.deal import Deal
from app.services.deal_service import DealService
from app.services.deal_access_service import DealAccessService
from app.services.commission_service import CommissionService
from app.models.user import UserModel, UserRole
from app.routers.auth import get_current_user, require_role, require_active_subscription

router = APIRouter(prefix="/deals", tags=["Deals"])


@router.get("/agent/my")
def get_agent_deals(
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("AGENT")),
):
    return DealService.get_for_agent(db, user.id)


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

    if not DealAccessService.can_view_deal(user, deal):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this deal",
        )

    return deal


@router.get("/{deal_id}/contacts")
def get_deal_contacts(
    deal_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()

    if deal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deal not found",
        )

    try:
        DealAccessService.require_contact_access(user, deal)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Deal contact access denied",
        )

    def serialize_user(party):
        if party is None:
            return None

        return {
            "id": party.id,
            "full_name": party.full_name,
            "email": party.email,
            "phone_number": party.phone_number,
        }

    locations = []
    if deal.listing is not None:
        for location in deal.listing.locations:
            locations.append(
                {
                    "country": location.country,
                    "state_province": location.state_province,
                    "locality": location.locality,
                    "address": location.address,
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                }
            )

    return {
        "deal_id": deal.id,
        "buyer": serialize_user(deal.buyer),
        "merchant": serialize_user(deal.merchant),
        "agent": serialize_user(deal.agent),
        "locations": locations,
    }


@router.post("/{deal_id}/approve")
def approve_deal(
    deal_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("BUYER")),
        _subscription_user: UserModel = Depends(require_active_subscription),
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
    user: UserModel = Depends(get_current_user),
    _subscription_user: UserModel = Depends(require_active_subscription),
):
    if user.role not in (UserRole.MERCHANT, UserRole.AGENT):
        raise HTTPException(
            status_code=403,
            detail="Only the merchant or assigned agent can mark the deal as delivered",
        )

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
        _subscription_user: UserModel = Depends(require_active_subscription),
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
    _subscription_user: UserModel = Depends(require_active_subscription),
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

@router.post("/{deal_id}/commission/accept")
def accept_deal_commission(
    deal_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("MERCHANT")),
        _subscription_user: UserModel = Depends(require_active_subscription),
):
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if deal is None:
        raise HTTPException(status_code=404, detail="Deal not found")

    commission = CommissionService.get_for_deal(db, deal.id)
    if commission is None:
        raise HTTPException(status_code=404, detail="Commission not found")

    try:
        accepted = CommissionService.accept_by_merchant(
            db,
            commission,
            user.id,
        )
        db.commit()
        db.refresh(accepted)
        return accepted
    except PermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc))
