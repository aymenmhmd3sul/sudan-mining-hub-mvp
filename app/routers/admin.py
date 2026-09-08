from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.models.user import UserModel
from app.models.commission import Commission
from app.models.deal import Deal
from app.models.negotiation import NegotiationRoom, NegotiationMessage
from app.models.offer import Offer
from app.routers.auth import require_role
from app.db.session import get_db
from app.schemas.listing import ListingResponse, AdminListingReviewResponse
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


@router.get(
    "/listings/pending",
    response_model=list[AdminListingReviewResponse],
)
def list_pending_listings(
    db: Session = Depends(get_db),
    user=Depends(require_role("ADMIN")),
):
    listings = ListingService.list_pending(db)
    return [
        {
            "id": listing.id,
            "owner_id": listing.owner_id,
            "owner_name": (listing.owner.full_name or listing.owner.email),
            "owner_email": listing.owner.email,
            "owner_phone": listing.owner.phone_number,
            "category_id": listing.category_id,
            "title": listing.title,
            "description": listing.description,
            "listing_type": listing.listing_type,
            "price": listing.price,
            "currency": listing.currency,
            "is_negotiable": listing.is_negotiable,
            "status": listing.status,
            "version": listing.version,
            "created_at": listing.created_at,
            "updated_at": listing.updated_at,
        }
        for listing in listings
    ]


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



@router.get("/negotiations")
def admin_negotiations(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role("ADMIN")),
):
    rooms = (
        db.query(NegotiationRoom)
        .order_by(
            NegotiationRoom.updated_at.desc(),
            NegotiationRoom.id.desc(),
        )
        .all()
    )

    room_rows = []

    for room in rooms:
        request_obj = room.request
        listing = request_obj.listing if request_obj is not None else None

        latest_message = (
            db.query(NegotiationMessage)
            .filter(NegotiationMessage.room_id == room.id)
            .order_by(
                NegotiationMessage.created_at.desc(),
                NegotiationMessage.id.desc(),
            )
            .first()
        )

        room_rows.append(
            {
                "room": room,
                "request_obj": request_obj,
                "listing": listing,
                "participants_count": len(room.participants),
                "messages_count": len(room.messages),
                "latest_message": latest_message,
            }
        )

    context = template_context(request)
    context.update(
        {
            "title": "غرف التفاوض",
            "current_user": user,
            "rooms": room_rows,
        }
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/negotiations.html",
        context=context,
    )


@router.get("/negotiations/{room_id}")
def admin_negotiation_report(
    room_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role("ADMIN")),
):
    room = (
        db.query(NegotiationRoom)
        .filter(NegotiationRoom.id == room_id)
        .first()
    )

    if room is None:
        raise HTTPException(
            status_code=404,
            detail="Negotiation room not found",
        )

    request_obj = room.request
    listing = request_obj.listing if request_obj is not None else None

    messages = (
        db.query(NegotiationMessage)
        .filter(NegotiationMessage.room_id == room.id)
        .order_by(
            NegotiationMessage.created_at.asc(),
            NegotiationMessage.id.asc(),
        )
        .all()
    )

    offers = (
        db.query(Offer)
        .filter(Offer.request_id == request_obj.id)
        .order_by(
            Offer.created_at.asc(),
            Offer.id.asc(),
        )
        .all()
    ) if request_obj is not None else []

    context = template_context(request)
    context.update(
        {
            "title": f"تقرير التفاوض #{room.id}",
            "current_user": user,
            "room": room,
            "request_obj": request_obj,
            "listing": listing,
            "messages": messages,
            "offers": offers,
            "participants": room.participants,
        }
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/negotiation_report.html",
        context=context,
    )


@router.get(
    "/deals",
)
def admin_deals(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role("ADMIN")),
):
    deals = (
        db.query(Deal)
        .order_by(Deal.created_at.desc(), Deal.id.desc())
        .all()
    )

    deal_rows = []

    for deal in deals:
        buyer = db.query(UserModel).filter(UserModel.id == deal.buyer_id).first()
        merchant = db.query(UserModel).filter(UserModel.id == deal.merchant_id).first()
        commission = (
            db.query(Commission)
            .filter(Commission.deal_id == deal.id)
            .first()
        )

        request_obj = deal.request
        listing = deal.listing

        location_parts = []

        if request_obj is not None and request_obj.target_location:
            location_parts.append(str(request_obj.target_location))

        if listing is not None:
            for listing_location in getattr(listing, "locations", []) or []:
                for value in (
                    getattr(listing_location, "address", None),
                    getattr(listing_location, "locality", None),
                    getattr(listing_location, "state_province", None),
                ):
                    if value:
                        location_parts.append(str(value))

        location = " — ".join(dict.fromkeys(location_parts)) or "-"

        deal_rows.append(
            {
                "deal": deal,
                "buyer": buyer,
                "merchant": merchant,
                "commission": commission,
                "location": location,
            }
        )

    context = template_context(request)
    context.update(
        {
            "title": "الصفقات والعمولات",
            "current_user": user,
            "deals": deal_rows,
        }
    )

    return templates.TemplateResponse(
        request=request,
        name="admin/deals.html",
        context=context,
    )


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

