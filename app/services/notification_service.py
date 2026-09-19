from datetime import datetime, timezone

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
    ) -> Notification:
        user = db.execute(
            select(UserModel).where(UserModel.id == recipient_user_id)
        ).scalar_one_or_none()

        if user is None:
            raise ValueError("Notification recipient does not exist")

        notification = Notification(
            recipient_user_id=recipient_user_id,
            event_type=event_type,
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
    def list_for_user(
        db: Session,
        user_id: int,
        *,
        limit: int = 50,
    ) -> list[Notification]:
        if limit < 1:
            raise ValueError("limit must be greater than zero")

        if limit > 100:
            limit = 100

        return list(
            db.execute(
                select(Notification)
                .where(Notification.recipient_user_id == user_id)
                .order_by(Notification.created_at.desc(), Notification.id.desc())
                .limit(limit)
            ).scalars()
        )

    @staticmethod
    def mark_sent(
        db: Session,
        notification: Notification,
    ) -> Notification:
        notification.status = NotificationStatus.SENT
        notification.sent_at = datetime.now(timezone.utc)
        notification.error_message = None
        db.flush()
        return notification

    @staticmethod
    def mark_failed(
        db: Session,
        notification: Notification,
        error_message: str,
    ) -> Notification:
        notification.status = NotificationStatus.FAILED
        notification.error_message = error_message[:4000]
        db.flush()
        return notification

    @staticmethod
    def send_whatsapp(
        *,
        phone_number: str,
        message: str,
    ) -> None:
        raise RuntimeError(
            "WhatsApp delivery provider is not configured yet"
        )
