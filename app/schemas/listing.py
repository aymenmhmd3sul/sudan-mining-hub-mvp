from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.listing import ListingType


class ListingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category_id: int = Field(gt=0)
    listing_type: ListingType = ListingType.ASSET
    price: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    is_negotiable: bool = True


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
