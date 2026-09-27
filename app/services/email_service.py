import hashlib
import json
import secrets
import urllib.error
import urllib.request

from app.core.config import settings


def generate_verification_token() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_verification_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def send_verification_email(email: str, token: str) -> None:
    if not settings.BREVO_API_KEY:
        raise RuntimeError("Email delivery is not configured: BREVO_API_KEY")

    if not settings.SENDER_EMAIL:
        raise RuntimeError("Email delivery is not configured: SENDER_EMAIL")

    payload = {
        "sender": {
            "name": settings.SENDER_NAME,
            "email": settings.SENDER_EMAIL,
        },
        "to": [
            {
                "email": email,
            }
        ],
        "subject": "Sudan Mining Hub - Email verification code",
        "textContent": (
            "Welcome to Sudan Mining Hub.\n\n"
            "Your email verification code is:\n\n"
            f"{token}\n\n"
            "This code is valid for "
            f"{settings.EMAIL_VERIFICATION_EXPIRE_HOURS} hours."
        ),
    }

    request = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": settings.BREVO_API_KEY,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(
                    f"Brevo email API returned HTTP {response.status}"
                )
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Brevo email API returned HTTP {exc.code}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Brevo email API connection failed"
        ) from exc
