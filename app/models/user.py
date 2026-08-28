import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum as SQLEnum, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    MERCHANT = "MERCHANT"
    BUYER = "BUYER"
    AGENT = "AGENT"

class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.BUYER, nullable=False)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
