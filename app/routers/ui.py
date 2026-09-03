from fastapi import APIRouter, Request, Depends, HTTPException
from app.db.session import get_db
from app.services.listing_service import ListingService
from app.models.listing import ListingStatus
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
def negotiation_page(request: Request):
    return render(
        request,
        "negotiation/negotiation.html",
        "pages.negotiation.title",
    )


@router.get("/services")
def services_page(request: Request):
    return render(
        request,
        "services/services.html",
        "pages.services.title",
    )
