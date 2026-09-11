from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.subscription import Subscription, SubscriptionStatus


class SubscriptionService:
    @staticmethod
    def get_for_user(
        db: Session,
        user_id: int,
    ) -> Subscription | None:
        return (
            db.query(Subscription)
            .filter(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .first()
        )

    @staticmethod
    def get_active_for_user(
        db: Session,
        user_id: int,
    ) -> Subscription | None:
        now = datetime.now(timezone.utc)

        subscription = (
            db.query(Subscription)
            .filter(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
            .order_by(Subscription.started_at.desc())
            .first()
        )

        if subscription is None:
            return None

        if (
            subscription.expires_at is not None
            and subscription.expires_at <= now
        ):
            subscription.status = SubscriptionStatus.EXPIRED
            db.flush()
            return None

        return subscription

    @staticmethod
    def is_active(
        db: Session,
        user_id: int,
    ) -> bool:
        return SubscriptionService.get_active_for_user(db, user_id) is not None

    @staticmethod
    def activate(
        db: Session,
        *,
        user_id: int,
        plan: str,
        expires_at: datetime | None = None,
        payment_reference: str | None = None,
        renewal_reference: str | None = None,
    ) -> Subscription:
        if not plan or not plan.strip():
            raise ValueError("Subscription plan is required")

        now = datetime.now(timezone.utc)

        current = SubscriptionService.get_active_for_user(
            db,
            user_id,
        )

        if current is not None:
            current.plan = plan.strip()
            current.expires_at = expires_at
            current.payment_reference = payment_reference
            current.renewal_reference = renewal_reference
            current.updated_at = now
            db.flush()
            return current

        subscription = Subscription(
            user_id=user_id,
            plan=plan.strip(),
            status=SubscriptionStatus.ACTIVE,
            started_at=now,
            expires_at=expires_at,
            cancelled_at=None,
            renewal_reference=renewal_reference,
            payment_reference=payment_reference,
            created_at=now,
            updated_at=now,
        )

        db.add(subscription)
        db.flush()
        return subscription

    @staticmethod
    def cancel(
        db: Session,
        subscription: Subscription,
    ) -> Subscription:
        if subscription.status in {
            SubscriptionStatus.CANCELLED,
            SubscriptionStatus.EXPIRED,
        }:
            raise ValueError(
                "Only active or pending subscriptions can be cancelled"
            )

        subscription.status = SubscriptionStatus.CANCELLED
        subscription.cancelled_at = datetime.now(timezone.utc)
        subscription.updated_at = datetime.now(timezone.utc)
        db.flush()
        return subscription

    @staticmethod
    def expire_if_needed(
        db: Session,
        subscription: Subscription,
    ) -> Subscription:
        if (
            subscription.status == SubscriptionStatus.ACTIVE
            and subscription.expires_at is not None
            and subscription.expires_at <= datetime.now(timezone.utc)
        ):
            subscription.status = SubscriptionStatus.EXPIRED
            subscription.updated_at = datetime.now(timezone.utc)
            db.flush()

        return subscription
