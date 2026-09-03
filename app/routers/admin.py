from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates

from app.models.user import UserModel
from app.routers.auth import require_role
from app.db.session import get_db
from app.schemas.listing import ListingResponse
from app.services.listing_service import ListingService
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
