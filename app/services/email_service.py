import hashlib
import secrets
import smtplib
from email.message import EmailMessage

from app.core.config import settings


def generate_verification_token() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def send_verification_email(email: str, token: str) -> None:
    required = {
        "SMTP_HOST": settings.SMTP_HOST,
        "SMTP_USERNAME": settings.SMTP_USERNAME,
        "SMTP_PASSWORD": settings.SMTP_PASSWORD,
        "SMTP_FROM": settings.SMTP_FROM,
    }

    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Email delivery is not configured: " + ", ".join(missing)
        )

    message = EmailMessage()
    message["Subject"] = "Sudan Mining Hub - Email verification code"
    message["From"] = settings.SMTP_FROM
    message["To"] = email
    message.set_content(
        "Welcome to Sudan Mining Hub.\n\n"
        "Your email verification code is:\n\n"
        f"{token}\n\n"
        f"This code is valid for "
        f"{settings.EMAIL_VERIFICATION_EXPIRE_HOURS} hours."
    )

    if settings.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
