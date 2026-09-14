from calendar import monthrange
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.subscription_payment import (
    SubscriptionPayment,
    SubscriptionPaymentStatus,
)
from app.models.subscription_pricing import SubscriptionPricing
from app.services.subscription_service import SubscriptionService


class SubscriptionBillingService:
    @staticmethod
    def get_active_price(
        db: Session,
        *,
        plan: str,
        currency: str,
    ) -> SubscriptionPricing | None:
        return (
            db.query(SubscriptionPricing)
            .filter(
                SubscriptionPricing.plan == plan.strip(),
                SubscriptionPricing.currency == currency.upper(),
                SubscriptionPricing.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def set_price(
        db: Session,
        *,
        plan: str,
        currency: str,
        amount: Decimal,
        billing_period_months: int = 1,
    ) -> SubscriptionPricing:
        plan = plan.strip()
        currency = currency.upper()

        if not plan:
            raise ValueError("Subscription plan is required")
        if len(currency) != 3:
            raise ValueError("Currency must be a 3-letter code")
        if amount < Decimal("0"):
            raise ValueError("Subscription price cannot be negative")
        if billing_period_months < 1:
            raise ValueError("Billing period must be at least one month")

        current = SubscriptionBillingService.get_active_price(
            db,
            plan=plan,
            currency=currency,
        )

        if current is not None:
            current.is_active = False
            db.flush()

        pricing = SubscriptionPricing(
            plan=plan,
            currency=currency,
            amount=amount,
            billing_period_months=billing_period_months,
            is_active=True,
        )
        db.add(pricing)
        db.flush()
        return pricing

    @staticmethod
    def create_payment(
        db: Session,
        *,
        user_id: int,
        plan: str,
        currency: str,
        payment_method: str | None = None,
        provider: str | None = None,
        external_reference: str | None = None,
    ) -> SubscriptionPayment:
        plan = plan.strip()
        currency = currency.upper()

        if not plan:
            raise ValueError("Subscription plan is required")
        if len(currency) != 3:
            raise ValueError("Currency must be a 3-letter code")

        pricing = SubscriptionBillingService.get_active_price(
            db,
            plan=plan,
            currency=currency,
        )

        if pricing is None:
            raise ValueError(
                f"No active subscription price for plan={plan!r}, "
                f"currency={currency!r}"
            )

        payment = SubscriptionPayment(
            user_id=user_id,
            subscription_id=None,
            plan=pricing.plan,
            amount=pricing.amount,
            currency=pricing.currency,
            status=SubscriptionPaymentStatus.PENDING,
            payment_method=payment_method,
            provider=provider,
            external_reference=external_reference,
            paid_at=None,
            verified_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(payment)
        db.flush()
        return payment

    @staticmethod
    def mark_paid(
        db: Session,
        payment: SubscriptionPayment,
        *,
        provider: str | None = None,
        external_reference: str | None = None,
    ) -> SubscriptionPayment:
        if payment.status == SubscriptionPaymentStatus.PAID:
            return payment

        if payment.status != SubscriptionPaymentStatus.PENDING:
            raise ValueError("Only pending payments can be marked as paid")

        now = datetime.now(timezone.utc)

        payment.status = SubscriptionPaymentStatus.PAID
        payment.provider = provider or payment.provider
        payment.external_reference = (
            external_reference or payment.external_reference
        )
        payment.paid_at = now
        payment.verified_at = now
        payment.updated_at = now

        db.flush()
        return payment

    @staticmethod
    def _add_months(value: datetime, months: int) -> datetime:
        month_index = value.month - 1 + months
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        day = min(value.day, monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)

    @staticmethod
    def activate_paid_payment(
        db: Session,
        payment: SubscriptionPayment,
    ):
        if payment.status != SubscriptionPaymentStatus.PAID:
            raise ValueError("Only paid payments can activate a subscription")

        if payment.verified_at is None:
            raise ValueError("Payment must be verified before activation")

        if payment.subscription_id is not None:
            raise ValueError("Payment is already linked to a subscription")

        pricing = SubscriptionBillingService.get_active_price(
            db,
            plan=payment.plan,
            currency=payment.currency,
        )

        if pricing is None:
            raise ValueError(
                f"No active subscription price for plan={payment.plan!r}, "
                f"currency={payment.currency!r}"
            )

        now = datetime.now(timezone.utc)

        current = SubscriptionService.get_active_for_user(
            db,
            payment.user_id,
        )

        base = now
        if current is not None and current.expires_at is not None:
            current_expiry = current.expires_at
            if current_expiry.tzinfo is None:
                current_expiry = current_expiry.replace(tzinfo=timezone.utc)
            if current_expiry > base:
                base = current_expiry

        expires_at = SubscriptionBillingService._add_months(
            base,
            pricing.billing_period_months,
        )

        subscription = SubscriptionService.activate(
            db,
            user_id=payment.user_id,
            plan=payment.plan,
            expires_at=expires_at,
            payment_reference=payment.external_reference,
            renewal_reference=payment.external_reference,
        )

        payment.subscription_id = subscription.id
        payment.updated_at = now

        db.flush()
        return subscription
