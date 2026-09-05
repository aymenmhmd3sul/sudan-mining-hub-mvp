from fastapi import APIRouter, Request, Depends, HTTPException
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
from app.routers.auth import require_role
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.translations.templates import template_context

router = APIRouter(tags=["UI"])

templates = Jinja2Templates(directory="app/templates")


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
    user=Depends(require_role("BUYER")),
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
def marketplace_page(request: Request):
    return render(
        request,
        "marketplace/marketplace.html",
        "pages.marketplace.title",
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

    request_obj = room.request

    if request_obj is None:
        raise HTTPException(status_code=404, detail="Negotiation request not found")

    listing = request_obj.listing

    messages = (
        db.query(NegotiationMessage)
        .filter(NegotiationMessage.room_id == room.id)
        .order_by(NegotiationMessage.created_at.asc(), NegotiationMessage.id.asc())
        .all()
    )

    offers = (
        db.query(Offer)
        .filter(Offer.request_id == request_obj.id)
        .order_by(Offer.created_at.asc(), Offer.id.asc())
        .all()
    )

    context = template_context(request)
    context.update(
        {
            "title": context["t"]("pages.negotiation.title"),
            "room": room,
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
