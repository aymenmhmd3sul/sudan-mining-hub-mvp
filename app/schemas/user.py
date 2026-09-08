from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr

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
    role: UserRole
    is_approved: bool
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
