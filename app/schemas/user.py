from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import UserRole

# مخطط إنشاء مستخدم جديد
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: UserRole = UserRole.BUYER

# مخطط إرجاع بيانات المستخدم (Response)
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

# مخطط تسجيل الدخول
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# مخطط الـ Token
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
