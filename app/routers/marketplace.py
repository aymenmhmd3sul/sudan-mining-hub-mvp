from pathlib import Path
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.listing import Listing, ListingStatus, ListingType
from app.models.listing_category import ListingCategory
from app.models.listing_media import ListingMedia, MediaType
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




@router.post("/{listing_id}/images")
async def upload_listing_image(
    listing_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserModel = Depends(require_role("MERCHANT", "ADMIN")),
):
    listing = (
        db.query(Listing)
        .filter(Listing.id == listing_id)
        .first()
    )

    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    if user.role != "ADMIN" and listing.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    allowed_types = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    suffix = allowed_types.get(file.content_type or "")
    if suffix is None:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, PNG, and WEBP images are allowed",
        )

    data = await file.read(5 * 1024 * 1024 + 1)

    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Image must not exceed 5 MB",
        )

    if not data:
        raise HTTPException(status_code=400, detail="Empty image")

    upload_dir = Path("app/static/uploads/listings")
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{listing_id}-{uuid.uuid4().hex}{suffix}"
    target = upload_dir / filename
    target.write_bytes(data)

    next_order = (
        db.query(ListingMedia)
        .filter(ListingMedia.listing_id == listing_id)
        .count()
    )

    media = ListingMedia(
        listing_id=listing_id,
        media_type=MediaType.IMAGE,
        url=f"/uploads/listings/{filename}",
        sort_order=next_order,
    )

    db.add(media)
    db.commit()
    db.refresh(media)

    return {
        "id": media.id,
        "listing_id": listing_id,
        "media_type": media.media_type,
        "url": media.url,
        "sort_order": media.sort_order,
    }

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
