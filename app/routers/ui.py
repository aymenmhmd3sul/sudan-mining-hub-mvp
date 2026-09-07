from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends, HTTPException, Cookie
from app.db.session import get_db
from app.services.listing_service import ListingService
from app.services.negotiation_service import NegotiationService
from app.models.listing import ListingStatus
from app.models.buyer_request import BuyerRequest, RequestStatus
from app.models.request_item import RequestItem
from app.models.negotiation import (
    NegotiationRoom,
    NegotiationParticipant,
    NegotiationMessage,
    NegotiationStatus,
)
from app.models.offer import Offer
from app.models.user import UserModel
from app.routers.auth import get_current_user, require_role
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.translations.templates import template_context

router = APIRouter(tags=["UI"])

templates = Jinja2Templates(directory="app/templates")


def get_optional_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not access_token:
        return None

    try:
        return get_current_user(access_token=access_token, db=db)
    except HTTPException:
        return None


def render(request: Request, template_name: str, title_key: str):
    context = template_context(request)
    context["title"] = context["t"](title_key)

    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context=context,
    )


@router.get("/register")
def register_page(request: Request):
    return render(
        request,
        "auth/register.html",
        "pages.register.title",
    )

@router.get("/login")
def login_page(request: Request):
    return render(
        request,
        "auth/login.html",
        "pages.login.title",
    )


@router.get("/merchant")
def merchant_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(require_role("MERCHANT")),
):
    pending_offers_count = (
        db.query(Offer)
        .filter(
            Offer.merchant_id == user.id,
            Offer.status == "SUBMITTED",
        )
        .count()
    )

    context = template_context(request)
    context.update(
        {
            "title": context["t"]("dashboard.merchant_label"),
            "current_user": user,
            "role": "MERCHANT",
            "pending_offers_count": pending_offers_count,
        }
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard/dashboard.html",
        context=context,
    )


@router.get("/marketplace/listing/{listing_id}")
def marketplace_listing_detail(
    listing_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    listing = ListingService.get_by_id(db, listing_id)

    if listing is None or listing.status != ListingStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Listing not found")

    context = template_context(request)
    context["listing"] = listing

    return templates.TemplateResponse(
        request=request,
        name="marketplace/listing_detail.html",
        context=context,
    )


@router.post("/api/v1/listings/{listing_id}/negotiate")
def start_listing_negotiation(
    listing_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    listing = ListingService.get_by_id(db, listing_id)

    if listing is None or listing.status != ListingStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Listing not found")

    if not listing.is_negotiable:
        raise HTTPException(
            status_code=400,
            detail="Listing is not open for negotiation",
        )

    if listing.owner_id == user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot negotiate your own listing",
        )

    existing_room = (
        db.query(NegotiationRoom)
        .join(
            BuyerRequest,
            BuyerRequest.id == NegotiationRoom.request_id,
        )
        .filter(
            BuyerRequest.buyer_id == user.id,
            BuyerRequest.listing_id == listing.id,
            NegotiationRoom.status == NegotiationStatus.OPEN,
        )
        .order_by(NegotiationRoom.id.desc())
        .first()
    )

    if existing_room is not None:
        return {
            "id": existing_room.id,
            "request_id": existing_room.request_id,
            "listing_id": listing.id,
            "status": existing_room.status,
            "existing": True,
        }

    request = BuyerRequest(
        buyer_id=user.id,
        listing_id=listing.id,
        title=listing.title,
        description=listing.description,
        status=RequestStatus.OPEN,
        currency=listing.currency,
    )
    db.add(request)
    db.flush()

    request_item = RequestItem(
        request_id=request.id,
        category_id=listing.category_id,
        title=listing.title,
        description=listing.description,
        quantity=1,
        unit="listing",
    )
    db.add(request_item)
    db.flush()

    room = NegotiationRoom(
        request_id=request.id,
        status=NegotiationStatus.OPEN,
    )
    db.add(room)
    db.flush()

    db.add_all(
        [
            NegotiationParticipant(
                room_id=room.id,
                user_id=user.id,
            ),
            NegotiationParticipant(
                room_id=room.id,
                user_id=listing.owner_id,
            ),
        ]
    )

    db.commit()
    db.refresh(room)

    return {
        "id": room.id,
        "request_id": request.id,
        "listing_id": listing.id,
        "status": room.status,
        "existing": False,
    }


@router.get("/marketplace")
def marketplace_page(
    request: Request,
    user=Depends(get_optional_current_user),
):
    context = template_context(request)
    context["title"] = context["t"]("pages.marketplace.title")
    context["current_user"] = user

    return templates.TemplateResponse(
        request=request,
        name="marketplace/marketplace.html",
        context=context,
    )


@router.get("/requests")
def requests_page(request: Request):
    return render(
        request,
        "requests/requests.html",
        "pages.requests.title",
    )


@router.get("/negotiation")
def negotiation_page(
    request: Request,
    room_id: int | None = None,
    db: Session = Depends(get_db),
    user=Depends(require_role("BUYER", "MERCHANT")),
):
    if room_id is not None:
        room = NegotiationService.get_room(db, room_id)
    else:
        room = (
            db.query(NegotiationRoom)
            .join(
                NegotiationParticipant,
                NegotiationParticipant.room_id == NegotiationRoom.id,
            )
            .filter(
                NegotiationParticipant.user_id == user.id,
                NegotiationRoom.status == NegotiationStatus.OPEN,
            )
            .order_by(NegotiationRoom.id.desc())
            .first()
        )

    if room_id is not None and room is None:
        raise HTTPException(status_code=404, detail="Negotiation room not found")

    if room is not None:
        participant = (
            db.query(NegotiationParticipant)
            .filter(
                NegotiationParticipant.room_id == room.id,
                NegotiationParticipant.user_id == user.id,
            )
            .first()
        )

        if participant is None:
            raise HTTPException(status_code=403, detail="You are not a participant in this negotiation")

        # Opening the room marks it as read for the current participant.
        participant.last_read_at = datetime.now(timezone.utc)
        db.commit()

    inbox_rooms = []

    for candidate in (
        db.query(NegotiationRoom)
        .join(
            NegotiationParticipant,
            NegotiationParticipant.room_id == NegotiationRoom.id,
        )
        .filter(NegotiationParticipant.user_id == user.id)
        .order_by(NegotiationRoom.updated_at.desc(), NegotiationRoom.id.desc())
        .all()
    ):
        candidate_participant = (
            db.query(NegotiationParticipant)
            .filter(
                NegotiationParticipant.room_id == candidate.id,
                NegotiationParticipant.user_id == user.id,
            )
            .first()
        )

        latest_message = (
            db.query(NegotiationMessage)
            .filter(NegotiationMessage.room_id == candidate.id)
            .order_by(
                NegotiationMessage.created_at.desc(),
                NegotiationMessage.id.desc(),
            )
            .first()
        )

        unread_query = db.query(NegotiationMessage).filter(
            NegotiationMessage.room_id == candidate.id,
            NegotiationMessage.sender_id != user.id,
        )

        if (
            candidate_participant is not None
            and candidate_participant.last_read_at is not None
        ):
            unread_query = unread_query.filter(
                NegotiationMessage.created_at
                > candidate_participant.last_read_at
            )

        unread_count = unread_query.count()

        other_participant = (
            db.query(NegotiationParticipant)
            .join(UserModel, UserModel.id == NegotiationParticipant.user_id)
            .filter(
                NegotiationParticipant.room_id == candidate.id,
                NegotiationParticipant.user_id != user.id,
            )
            .first()
        )

        inbox_rooms.append(
            {
                "room": candidate,
                "latest_message": latest_message,
                "other_user": (
                    other_participant.user
                    if other_participant
                    else None
                ),
                "unread_count": unread_count,
                "is_new": (
                    candidate_participant is not None
                    and candidate_participant.last_read_at is None
                ),
            }
        )

    request_obj = room.request if room is not None else None

    listing = request_obj.listing if request_obj is not None else None

    messages = (
        db.query(NegotiationMessage)
        .filter(NegotiationMessage.room_id == room.id)
        .order_by(
            NegotiationMessage.created_at.asc(),
            NegotiationMessage.id.asc(),
        )
        .all()
    ) if room is not None else []

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
            "title": context["t"]("pages.negotiation.title"),
            "room": room,
            "inbox_rooms": inbox_rooms,
            "request_obj": request_obj,
            "listing": listing,
            "messages": messages,
            "offers": offers,
            "current_user": user,
        }
    )

    return templates.TemplateResponse(
        request=request,
        name="negotiation/negotiation.html",
        context=context,
    )


@router.post("/api/v1/negotiation/{room_id}/messages")
def send_negotiation_message(
    room_id: int,
    body: str,
    db: Session = Depends(get_db),
    user=Depends(require_role("BUYER", "MERCHANT")),
):
    room = NegotiationService.get_room(db, room_id)

    if room is None:
        raise HTTPException(status_code=404, detail="Negotiation room not found")

    participant = (
        db.query(NegotiationParticipant)
        .filter(
            NegotiationParticipant.room_id == room.id,
            NegotiationParticipant.user_id == user.id,
        )
        .first()
    )

    if participant is None:
        raise HTTPException(status_code=403, detail="You are not a participant in this negotiation")

    message_body = body.strip()

    if not message_body:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if room.status in (
        NegotiationStatus.CANCELLED,
        NegotiationStatus.CLOSED,
    ):
        raise HTTPException(status_code=400, detail="Negotiation room is closed")

    message = NegotiationService.add_message(
        db,
        room_id=room.id,
        sender_id=user.id,
        body=message_body,
    )

    return {
        "id": message.id,
        "room_id": message.room_id,
        "sender_id": message.sender_id,
        "body": message.body,
        "created_at": message.created_at,
    }


@router.get("/services")
def services_page(request: Request):
    return render(
        request,
        "services/services.html",
        "pages.services.title",
    )
