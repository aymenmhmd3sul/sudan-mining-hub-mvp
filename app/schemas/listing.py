from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.listing import ListingType
from app.models.listing_media import MediaType


class ListingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category_id: int = Field(gt=0)
    listing_type: ListingType = ListingType.ASSET
    price: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    is_negotiable: bool = True
    state_province: str | None = None
    locality: str | None = None
    address: str | None = None
    specs: str | None = None


class ListingMediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    media_type: MediaType
    url: str
    sort_order: int


class ListingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    category_id: int
    title: str
    description: str | None
    listing_type: ListingType
    price: float | None
    currency: str
    is_negotiable: bool
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
    images: list[ListingMediaResponse] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def load_media_as_images(cls, value):
        media = getattr(value, "media", None)
        if media is not None:
            image_media = [
                item for item in media
                if getattr(item, "media_type", None) == MediaType.IMAGE
            ]
            image_media.sort(
                key=lambda item: getattr(item, "sort_order", 0)
            )
            return {
                "id": value.id,
                "owner_id": value.owner_id,
                "category_id": value.category_id,
                "title": value.title,
                "description": value.description,
                "listing_type": value.listing_type,
                "price": value.price,
                "currency": value.currency,
                "is_negotiable": value.is_negotiable,
                "status": value.status,
                "version": value.version,
                "created_at": value.created_at,
                "updated_at": value.updated_at,
                "images": image_media,
            }
        return value


class AdminListingReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    owner_name: str
    owner_phone: str | None
    owner_email: str
    category_id: int
    title: str
    description: str | None
    listing_type: ListingType
    price: float | None
    currency: str
    is_negotiable: bool
    status: str
    version: int
    created_at: datetime
    updated_at: datetime
