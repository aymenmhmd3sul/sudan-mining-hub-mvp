from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.user import UserRole


class PublicRegistrationRole(str, Enum):
    MERCHANT = "MERCHANT"
    BUYER = "BUYER"
    AGENT = "AGENT"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: PublicRegistrationRole = PublicRegistrationRole.BUYER


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_opt_in: bool
    whatsapp_opt_in_at: Optional[datetime] = None
    role: UserRole
    is_approved: bool
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)

    @model_validator(mode="after")
    def passwords_must_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self
