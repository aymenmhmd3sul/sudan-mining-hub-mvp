from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CommissionSettingsCreate(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    commission_rate: Decimal = Field(ge=0, le=100)
    minimum_amount: Decimal | None = Field(default=None, ge=0)
    is_active: bool = True


class CommissionSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    currency: str
    commission_rate: Decimal
    minimum_amount: Decimal | None
    is_active: bool
