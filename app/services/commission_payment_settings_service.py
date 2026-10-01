from sqlalchemy.orm import Session

from app.models.commission_payment_settings import CommissionPaymentSettings


class CommissionPaymentSettingsService:
    @staticmethod
    def list_active(
        db: Session,
    ) -> list[CommissionPaymentSettings]:
        return (
            db.query(CommissionPaymentSettings)
            .filter(
                CommissionPaymentSettings.is_active.is_(True),
            )
            .order_by(CommissionPaymentSettings.currency)
            .all()
        )

    @staticmethod
    def get_active(
        db: Session,
        currency: str,
    ) -> CommissionPaymentSettings | None:
        return (
            db.query(CommissionPaymentSettings)
            .filter(
                CommissionPaymentSettings.currency == currency.upper(),
                CommissionPaymentSettings.is_active.is_(True),
            )
            .first()
        )

    @staticmethod
    def create(
        db: Session,
        *,
        currency: str,
        account_number: str | None,
        account_name: str | None,
        payment_instructions: str | None,
        is_active: bool = True,
    ) -> CommissionPaymentSettings:
        currency = currency.upper()

        if len(currency) != 3:
            raise ValueError("Currency must be a 3-letter code")

        if is_active:
            current = CommissionPaymentSettingsService.get_active(
                db,
                currency,
            )
            if current is not None:
                current.is_active = False
                db.flush()

        settings = CommissionPaymentSettings(
            currency=currency,
            account_number=account_number,
            account_name=account_name,
            payment_instructions=payment_instructions,
            is_active=is_active,
        )

        db.add(settings)
        db.flush()
        return settings
