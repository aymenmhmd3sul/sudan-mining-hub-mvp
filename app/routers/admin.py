from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.models.user import UserModel
from app.models.commission import Commission
from app.routers.auth import require_role
from app.db.session import get_db
from app.schemas.listing import ListingResponse
from app.schemas.commission_settings import (
    CommissionSettingsCreate,
    CommissionSettingsResponse,
)
from app.services.listing_service import ListingService
from app.services.commission_settings_service import CommissionSettingsService
from app.services.commission_service import CommissionService
from app.translations.templates import template_context

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/")
def admin_dashboard(
    request: Request,
    user: UserModel = Depends(require_role("ADMIN")),
):
    context = template_context(request)
    context["user"] = user

    return templates.TemplateResponse(
        request=request,
        name="admin/dashboard.html",
        context=context,
    )


@router.post(
    "/listings/{listing_id}/approve",
    response_model=ListingResponse,
)
def approve_listing(
    listing_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("ADMIN")),
):
    try:
        return ListingService.approve(db, listing_id)
    except ValueError as exc:
        detail = str(exc)

        if detail == "Listing not found":
            raise HTTPException(status_code=404, detail=detail)

        raise HTTPException(status_code=409, detail=detail)



@router.get(
    "/commission-settings",
    response_model=list[CommissionSettingsResponse],
)
def list_commission_settings(
    db: Session = Depends(get_db),
    user=Depends(require_role("ADMIN")),
):
    return CommissionSettingsService.list_active(db)


@router.post(
    "/commission-settings",
    response_model=CommissionSettingsResponse,
    status_code=201,
)
def create_commission_settings(
    payload: CommissionSettingsCreate,
    db: Session = Depends(get_db),
    user=Depends(require_role("ADMIN")),
):
    try:
        settings = CommissionSettingsService.create(
            db,
            currency=payload.currency,
            commission_rate=payload.commission_rate,
            minimum_amount=payload.minimum_amount,
            is_active=payload.is_active,
        )
        db.commit()
        db.refresh(settings)
        return settings

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))

@router.post(
    "/commissions/{commission_id}/settle",
)
def settle_commission(
    commission_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("ADMIN")),
):
    commission = (
        db.query(Commission)
        .filter(Commission.id == commission_id)
        .first()
    )

    if commission is None:
        raise HTTPException(
            status_code=404,
            detail="Commission not found",
        )

    try:
        commission = CommissionService.settle(
            db,
            commission,
        )
        db.commit()
        db.refresh(commission)
        return commission
    except ValueError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

