from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.commission_settings import CommissionSettings


class CommissionSettingsService:
    @staticmethod
    def list_active(db: Session) -> list[CommissionSettings]:
        return (
            db.query(CommissionSettings)
            .filter(CommissionSettings.is_active.is_(True))
            .order_by(CommissionSettings.currency)
            .all()
        )

    @staticmethod
    def get_active(
        db: Session,
        currency: str,
    ) -> CommissionSettings | None:
        return (
            db.query(CommissionSettings)
            .filter(
                CommissionSettings.currency == currency.upper(),
                CommissionSettings.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        *,
        currency: str,
        commission_rate: Decimal,
        minimum_amount: Decimal | None,
        is_active: bool = True,
    ) -> CommissionSettings:
        currency = currency.upper()

        if len(currency) != 3:
            raise ValueError("Currency must be a 3-letter code")

        if commission_rate < Decimal("0") or commission_rate > Decimal("100"):
            raise ValueError("Commission rate must be between 0 and 100")

        if minimum_amount is not None and minimum_amount < Decimal("0"):
            raise ValueError("Minimum commission cannot be negative")

        if is_active:
            current = CommissionSettingsService.get_active(db, currency)
            if current is not None:
                current.is_active = False
                db.flush()

        settings = CommissionSettings(
            currency=currency,
            commission_rate=commission_rate,
            minimum_amount=minimum_amount,
            is_active=is_active,
        )
        db.add(settings)
        db.flush()
        return settings
