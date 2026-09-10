import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import UserModel, UserRole
from app.core.security import get_password_hash


def main():
    database_url = settings.DATABASE_URL

    if not database_url:
        raise SystemExit(
            "STOP: DATABASE_URL is not configured. "
            "No database operation was performed."
        )

    if database_url.startswith("sqlite"):
        raise SystemExit(
            "STOP: SQLite is not allowed for ADMIN provisioning. "
            "Use the PostgreSQL database configured for this production environment."
        )

    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_name = os.getenv("ADMIN_FULL_NAME", "Aymen Muhammad")

    if not admin_email:
        raise SystemExit(
            "STOP: ADMIN_EMAIL is not set. "
            "No database operation was performed."
        )

    if not admin_password:
        raise SystemExit(
            "STOP: ADMIN_PASSWORD is not set. "
            "No database operation was performed."
        )

    if len(admin_password) < 12:
        raise SystemExit(
            "STOP: ADMIN_PASSWORD must be at least 12 characters."
        )

    db = SessionLocal()

    try:
        existing = (
            db.query(UserModel)
            .filter(UserModel.email == admin_email)
            .first()
        )

        if existing:
            if existing.role != UserRole.ADMIN:
                raise SystemExit(
                    "STOP: Existing account with ADMIN_EMAIL is not an ADMIN. "
                    "No database operation was performed."
                )

            print("ADMIN ALREADY EXISTS")
            print("id:", existing.id)
            print("email:", existing.email)
            print("role:", existing.role.value)
            print("is_approved:", existing.is_approved)
            return

        admin = UserModel(
            email=admin_email,
            hashed_password=get_password_hash(admin_password),
            full_name=admin_name,
            phone_number=None,
            role=UserRole.ADMIN,
            is_approved=True,
        )

        db.add(admin)
        db.commit()
        db.refresh(admin)

        print("ADMIN PROVISIONED SUCCESSFULLY")
        print("id:", admin.id)
        print("email:", admin.email)
        print("role:", admin.role.value)
        print("is_approved:", admin.is_approved)

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
