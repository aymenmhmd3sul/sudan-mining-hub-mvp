from datetime import datetime, timedelta, timezone
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Form, Request
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


def _auth_cookie_secure() -> bool:
    return settings.APP_BASE_URL.lower().startswith("https://")


def _set_auth_cookie(response: Response, access_token: str) -> None:
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=_auth_cookie_secure(),
        samesite="lax",
        path="/",
    )


def _delete_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key="access_token",
        secure=_auth_cookie_secure(),
        samesite="lax",
        path="/",
    )


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
    except Exception as exc:
        print(
            f"REGISTRATION_EMAIL_ERROR: {type(exc).__name__}: {exc}",
            flush=True,
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="تعذر إرسال رسالة تأكيد البريد الإلكتروني",
        )

    db.refresh(new_user)
    return new_user


# Login rate limiting: in-process for the current single-instance MVP.
LOGIN_RATE_LIMIT_WINDOW_SECONDS = 300
LOGIN_RATE_LIMIT_MAX_ATTEMPTS = 10
LOGIN_RATE_LIMIT_BLOCK_SECONDS = 300

_login_attempts = defaultdict(deque)
_login_blocked_until = {}


def _login_rate_limit_key(request: Request, email: str) -> str:
    host = request.client.host if request.client else "unknown"
    normalized_email = (email or "").strip().lower()
    return f"{host}:{normalized_email}"


def _check_login_rate_limit(request: Request, email: str):
    now = time.monotonic()
    key = _login_rate_limit_key(request, email)

    blocked_until = _login_blocked_until.get(key, 0)
    if blocked_until > now:
        return False, max(1, int(blocked_until - now))

    attempts = _login_attempts[key]
    cutoff = now - LOGIN_RATE_LIMIT_WINDOW_SECONDS

    while attempts and attempts[0] <= cutoff:
        attempts.popleft()

    if len(attempts) >= LOGIN_RATE_LIMIT_MAX_ATTEMPTS:
        blocked_until = now + LOGIN_RATE_LIMIT_BLOCK_SECONDS
        _login_blocked_until[key] = blocked_until
        return False, LOGIN_RATE_LIMIT_BLOCK_SECONDS

    return True, 0


def _record_login_attempt(request: Request, email: str):
    now = time.monotonic()
    key = _login_rate_limit_key(request, email)
    attempts = _login_attempts[key]
    cutoff = now - LOGIN_RATE_LIMIT_WINDOW_SECONDS

    while attempts and attempts[0] <= cutoff:
        attempts.popleft()

    attempts.append(now)


@router.post("/login", response_model=Token)
def login(
    user_credentials: UserLogin,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    allowed, retry_after = _check_login_rate_limit(
        request,
        user_credentials.email,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    _record_login_attempt(request, user_credentials.email)

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

    _set_auth_cookie(response, access_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/verify-email")
def verify_email(
    code: str = Form(...),
    db: Session = Depends(get_db),
):
    normalized_code = code.strip()

    if not normalized_code.isdigit() or len(normalized_code) != 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="رمز التحقق يجب أن يتكون من 6 أرقام",
        )

    code_hash = hash_verification_token(normalized_code)

    user = (
        db.query(UserModel)
        .filter(
            UserModel.email_verification_token_hash == code_hash,
            UserModel.email_verified.is_(False),
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="رمز التحقق غير صحيح",
        )

    expires_at = user.email_verification_expires_at
    if not expires_at or expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="انتهت صلاحية رمز التحقق",
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

        if (
            user.role == UserRole.MERCHANT
            and not user.is_approved
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Merchant approval required",
            )

        return user

    return role_guard


@router.post("/change-password")
def change_password(
    password_data: PasswordChange,
    response: Response,
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
    _delete_auth_cookie(response)

    return {"message": "تم تغيير كلمة المرور بنجاح"}


@router.post("/logout")
def logout(response: Response):
    _delete_auth_cookie(response)
    return {"message": "تم تسجيل الخروج بنجاح"}


@router.get("/me", response_model=UserOut)
def current_user(
    user: UserModel = Depends(get_current_user),
):
    return user


@router.post("/whatsapp-opt-in")
def whatsapp_opt_in(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    if not user.phone_number or not user.phone_number.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A phone number is required before enabling WhatsApp notifications.",
        )

    user.whatsapp_opt_in = True
    user.whatsapp_opt_in_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    return {
        "message": "تم تفعيل استقبال رسائل WhatsApp من Sudan Mining Hub",
        "whatsapp_opt_in": user.whatsapp_opt_in,
        "whatsapp_opt_in_at": user.whatsapp_opt_in_at,
    }


@router.delete("/whatsapp-opt-in")
def whatsapp_opt_out(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    user.whatsapp_opt_in = False
    user.whatsapp_opt_in_at = None
    db.commit()
    db.refresh(user)

    return {
        "message": "تم إلغاء استقبال رسائل WhatsApp من Sudan Mining Hub",
        "whatsapp_opt_in": user.whatsapp_opt_in,
        "whatsapp_opt_in_at": user.whatsapp_opt_in_at,
    }
