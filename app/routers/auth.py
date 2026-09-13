from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import UserModel, UserRole
from app.schemas.user import (
    UserCreate,
    UserOut,
    UserLogin,
    PasswordChange,
    Token,
)
from app.services.subscription_service import SubscriptionService
from app.services.email_service import (
    generate_verification_token,
    hash_verification_token,
    send_verification_email,
)
from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = (
        db.query(UserModel)
        .filter(UserModel.email == user_in.email)
        .first()
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="البريد الإلكتروني مسجل بالفعل",
        )

    verification_token = generate_verification_token()
    verification_token_hash = hash_verification_token(verification_token)
    verification_expires_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRE_HOURS)
    )

    new_user = UserModel(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        phone_number=user_in.phone_number,
        role=UserRole(user_in.role.value),
        email_verified=False,
        email_verification_token_hash=verification_token_hash,
        email_verification_expires_at=verification_expires_at,
    )

    db.add(new_user)

    try:
        send_verification_email(
            new_user.email,
            verification_token,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تعذر إرسال رسالة تأكيد البريد الإلكتروني",
        )

    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(
    user_credentials: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
):
    user = (
        db.query(UserModel)
        .filter(UserModel.email == user_credentials.email)
        .first()
    )

    if not user or not verify_password(
        user_credentials.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="بيانات الاعتماد غير صحيحة",
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="يرجى تأكيد البريد الإلكتروني أولًا",
        )

    access_token = create_access_token(
        data={
            "sub": user.email,
            "role": user.role.value,
        }
    )

    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/verify-email")
def verify_email(
    token: str,
    db: Session = Depends(get_db),
):
    token_hash = hash_verification_token(token)

    user = (
        db.query(UserModel)
        .filter(
            UserModel.email_verification_token_hash == token_hash,
            UserModel.email_verified.is_(False),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="رابط تأكيد البريد الإلكتروني غير صالح",
        )

    expires_at = user.email_verification_expires_at
    if not expires_at or expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="انتهت صلاحية رابط تأكيد البريد الإلكتروني",
        )

    user.email_verified = True
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    db.commit()

    return {"message": "تم تأكيد البريد الإلكتروني بنجاح"}


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    if access_token.startswith("Bearer "):
        access_token = access_token[7:]

    try:
        payload = decode_access_token(access_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    email = payload.get("sub")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = (
        db.query(UserModel)
        .filter(UserModel.email == email)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


def require_active_subscription(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    if user.role == UserRole.ADMIN:
        return user

    if not SubscriptionService.is_active(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active subscription required",
        )

    return user



def get_optional_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    if not access_token:
        return None

    if access_token.startswith("Bearer "):
        access_token = access_token[7:]

    try:
        payload = decode_access_token(access_token)
    except ValueError:
        return None

    email = payload.get("sub")
    if not email:
        return None

    return (
        db.query(UserModel)
        .filter(UserModel.email == email)
        .first()
    )

def require_role(*allowed_roles):
    def role_guard(
        user: UserModel = Depends(get_current_user),
    ):
        if user.role.value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_guard


@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    if not verify_password(
        password_data.current_password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="كلمة المرور الحالية غير صحيحة",
        )

    user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()

    return {"message": "تم تغيير كلمة المرور بنجاح"}


@router.get("/me", response_model=UserOut)
def current_user(
    user: UserModel = Depends(get_current_user),
):
    return user
