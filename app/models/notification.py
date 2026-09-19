import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class NotificationChannel(str, enum.Enum):
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    recipient_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type = Column(String(100), nullable=False, index=True)
    channel = Column(
        Enum(NotificationChannel),
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(NotificationStatus),
        nullable=False,
        default=NotificationStatus.PENDING,
        index=True,
    )

    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    related_type = Column(String(100), nullable=True)
    related_id = Column(Integer, nullable=True)

    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_notifications_recipient_created",
            "recipient_user_id",
            "created_at",
        ),
        Index(
            "ix_notifications_related",
            "related_type",
            "related_id",
        ),
    )
