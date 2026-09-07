from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.listing import ListingStatus, ListingType
from app.models.listing_category import ListingCategory
from app.models.user import UserModel
from app.routers.auth import require_role
from app.schemas.listing import ListingCreate, ListingResponse
from app.services.listing_service import ListingService


router = APIRouter(
    prefix="/api/v1/listings",
    tags=["Marketplace"],
)


@router.get("", response_model=list[ListingResponse])
def list_listings(
    limit: int = Query(default=100, ge=1, le=100),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    listing_type: ListingType | None = Query(default=None),
    category_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    return ListingService.list_active(
        db,
        limit=limit,
        search=search,
        listing_type=listing_type,
        category_id=category_id,
    )


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
):
    return (
        db.query(ListingCategory)
        .filter(ListingCategory.status == "ACTIVE")
        .order_by(ListingCategory.sort_order, ListingCategory.category_id)
        .all()
    )


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(
    listing_id: int,
    db: Session = Depends(get_db),
):
    listing = ListingService.get_by_id(db, listing_id)

    if listing is None or listing.status != ListingStatus.ACTIVE:
        raise HTTPException(status_code=404, detail="Listing not found")

    return listing


@router.post("", response_model=ListingResponse, status_code=201)
def create_listing(
    payload: ListingCreate,
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("MERCHANT", "ADMIN")),
):
    data = payload.model_dump()
    data["owner_id"] = user.id
    data["status"] = ListingStatus.DRAFT

    return ListingService.create(db, **data)
