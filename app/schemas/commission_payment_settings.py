from pydantic import BaseModel, ConfigDict, Field


class CommissionPaymentSettingsCreate(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    account_number: str | None = Field(default=None, max_length=255)
    account_name: str | None = Field(default=None, max_length=255)
    payment_instructions: str | None = Field(default=None, max_length=2000)
    is_active: bool = True


class CommissionPaymentSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    currency: str
    account_number: str | None
    account_name: str | None
    payment_instructions: str | None
    is_active: bool
