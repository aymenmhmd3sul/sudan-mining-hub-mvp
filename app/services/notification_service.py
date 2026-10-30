from datetime import datetime, timezone
import json
import logging

from app.core.config import settings
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from app.models.user import UserModel, UserRole
from app.services.push_endpoint import is_safe_push_endpoint
from app.translations.service import normalize_language


class NotificationService:
    @staticmethod
    def notify_admins_of_registration(
        db: Session,
        *,
        registered_user_id: int,
        registered_user_email: str,
    ) -> None:
        """Notify all admins about a registration without affecting signup."""
        try:
            admins = (
                db.query(UserModel)
                .filter(UserModel.role == UserRole.ADMIN)
                .all()
            )

            for admin in admins:
                NotificationService.create(
                    db,
                    recipient_user_id=admin.id,
                    event_type="admin_new_registration",
                    title="تسجيل مستخدم جديد",
                    message=f"تم تسجيل مستخدم جديد بالبريد: {registered_user_email}",
                    related_type="user",
                    related_id=registered_user_id,
                    event_key=(
                        f"admin_new_registration:"
                        f"{registered_user_id}:{admin.id}"
                    ),
                )

            db.commit()
        except Exception:
            db.rollback()
            logger.exception(
                "Could not create admin notifications for registration user %s",
                registered_user_id,
            )
            return

        for admin in admins:
            try:
                NotificationService.send_web_push(
                    db,
                    recipient_user_id=admin.id,
                    title="تسجيل مستخدم جديد",
                    message=f"تم تسجيل مستخدم جديد بالبريد: {registered_user_email}",
                    url="/admin/",
                )
            except Exception:
                logger.exception(
                    "Admin registration push failed for admin %s",
                    admin.id,
                )

    @staticmethod
    def create(
        db: Session,
        *,
        recipient_user_id: int,
        event_type: str,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        related_type: str | None = None,
        related_id: int | None = None,
        event_key: str | None = None,
    ) -> Notification:
        user = db.execute(
            select(UserModel).where(
                UserModel.id == recipient_user_id
            )
        ).scalar_one_or_none()

        if user is None:
            raise ValueError("Notification recipient does not exist")

        if event_key is not None:
            existing = db.execute(
                select(Notification).where(
                    Notification.event_key == event_key
                )
            ).scalar_one_or_none()

            if existing is not None:
                return existing

        notification = Notification(
            recipient_user_id=recipient_user_id,
            event_type=event_type,
            event_key=event_key,
            channel=channel,
            status=NotificationStatus.PENDING,
            title=title,
            message=message,
            related_type=related_type,
            related_id=related_id,
        )

        db.add(notification)
        db.flush()

        return notification

    @staticmethod
    def send_web_push(
        db: Session,
        *,
        recipient_user_id: int,
        title: str | dict,
        message: str | dict,
        url: str = "/",
    ) -> None:
        """Send best-effort Web Push without affecting the main operation."""
        if not settings.VAPID_PUBLIC_KEY or not settings.VAPID_PRIVATE_KEY:
            return

        try:
            from pywebpush import webpush
        except Exception:
            logger.exception("Web Push library could not be loaded")
            return

        try:
            subscriptions = db.query(PushSubscription).filter(
                PushSubscription.user_id == recipient_user_id
            ).all()
        except Exception:
            logger.exception(
                "Could not load push subscriptions for user %s",
                recipient_user_id,
            )
            return

        for subscription in subscriptions:
            if not is_safe_push_endpoint(subscription.endpoint):
                logger.warning(
                    "Skipping unsafe Web Push endpoint for user %s",
                    recipient_user_id,
                )
                continue

            language = normalize_language(getattr(subscription, "language", "ar"))
            localized_title = title.get(language, title.get("ar", "")) if isinstance(title, dict) else title
            localized_message = message.get(language, message.get("ar", "")) if isinstance(message, dict) else message
            payload = json.dumps({
                "title": localized_title,
                "body": localized_message,
                "url": url,
            }, ensure_ascii=False)
            try:
                webpush(
                    subscription_info={
                        "endpoint": subscription.endpoint,
                        "keys": {
                            "p256dh": subscription.p256dh,
                            "auth": subscription.auth,
                        },
                    },
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={
                        "sub": settings.VAPID_CLAIMS_EMAIL,
                    },
                )
            except Exception:
                logger.exception(
                    "Web Push delivery failed for user %s",
                    recipient_user_id,
                )
