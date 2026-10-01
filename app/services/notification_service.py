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
