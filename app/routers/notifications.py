from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.notification import Notification
from app.models.push_subscription import PushSubscription
from app.models.user import UserModel
from app.routers.auth import get_current_user

router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"],
)


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=512)
    auth: str = Field(min_length=1, max_length=512)


class PushSubscriptionPayload(BaseModel):
    endpoint: str = Field(min_length=10, max_length=4096)
    keys: PushSubscriptionKeys


def _notification_payload(notification: Notification) -> dict:
    return {
        "id": notification.id,
        "event_type": notification.event_type,
        "title": notification.title,
        "message": notification.message,
        "related_type": notification.related_type,
        "related_id": notification.related_id,
        "created_at": (
            notification.created_at.isoformat()
            if notification.created_at
            else None
        ),
        "read_at": (
            notification.read_at.isoformat()
            if notification.read_at
            else None
        ),
        "is_read": notification.read_at is not None,
    }


@router.get("")
def list_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    unread_count = (
        db.query(func.count(Notification.id))
        .filter(
            Notification.recipient_user_id == user.id,
            Notification.read_at.is_(None),
        )
        .scalar()
        or 0
    )

    notifications = (
        db.query(Notification)
        .filter(Notification.recipient_user_id == user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .all()
    )

    return {
        "unread_count": unread_count,
        "items": [_notification_payload(item) for item in notifications],
    }


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.recipient_user_id == user.id,
        )
        .first()
    )

    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)

    return {
        "ok": True,
        "notification": _notification_payload(notification),
    }


@router.patch("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)

    updated = (
        db.query(Notification)
        .filter(
            Notification.recipient_user_id == user.id,
            Notification.read_at.is_(None),
        )
        .update(
            {Notification.read_at: now},
            synchronize_session=False,
        )
    )

    db.commit()
    return {"ok": True, "updated_count": updated}


@router.get("/push-public-key")
def get_push_public_key(
    user: UserModel = Depends(get_current_user),
):
    from app.core.config import settings

    if not settings.VAPID_PUBLIC_KEY:
        return {"enabled": False}

    return {
        "enabled": True,
        "public_key": settings.VAPID_PUBLIC_KEY,
    }


@router.post("/push-subscription")
def register_push_subscription(
    payload: PushSubscriptionPayload,
    db: Session = Depends(get_db),
    user: UserModel = Depends(get_current_user),
):
    if not payload.endpoint.startswith("https://"):
        raise HTTPException(
            status_code=422,
            detail="Push subscription endpoint must use HTTPS",
        )

    subscription = (
        db.query(PushSubscription)
        .filter(PushSubscription.endpoint == payload.endpoint)
        .first()
    )

    if subscription is None:
        subscription = PushSubscription(
            user_id=user.id,
            endpoint=payload.endpoint,
            p256dh=payload.keys.p256dh,
            auth=payload.keys.auth,
        )
        db.add(subscription)
    else:
        if subscription.user_id != user.id:
            raise HTTPException(
                status_code=409,
                detail="Push subscription already belongs to another user",
            )
        subscription.p256dh = payload.keys.p256dh
        subscription.auth = payload.keys.auth
        subscription.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(subscription)

    return {
        "ok": True,
        "subscription_id": subscription.id,
    }
