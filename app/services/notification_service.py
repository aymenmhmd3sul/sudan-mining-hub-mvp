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
from app.models.user import UserModel


class NotificationService:
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
        title: str,
        message: str,
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

        payload = json.dumps({
            "title": title,
            "body": message,
            "url": url,
        })

        for subscription in subscriptions:
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
