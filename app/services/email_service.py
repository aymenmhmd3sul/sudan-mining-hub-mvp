import hashlib
import secrets

import resend

from app.core.config import settings


def generate_verification_token() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def send_verification_email(email: str, token: str) -> None:
    if not settings.RESEND_API_KEY:
        raise RuntimeError("Email delivery is not configured: RESEND_API_KEY")

    if not settings.EMAIL_FROM:
        raise RuntimeError("Email delivery is not configured: EMAIL_FROM")

    resend.api_key = settings.RESEND_API_KEY

    params: resend.Emails.SendParams = {
        "from": settings.EMAIL_FROM,
        "to": [email],
        "subject": "Sudan Mining Hub - Email verification code",
        "text": (
            "Welcome to Sudan Mining Hub.\n\n"
            "Your email verification code is:\n\n"
            f"{token}\n\n"
            "This code is valid for "
            f"{settings.EMAIL_VERIFICATION_EXPIRE_HOURS} hours."
        ),
    }

    resend.Emails.send(params)
