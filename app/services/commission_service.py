from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.commission import Commission, CommissionStatus
from app.models.commission_settings import CommissionSettings


class CommissionService:
    @staticmethod
    def get_active_settings(
        db: Session,
        currency: str,
    ) -> CommissionSettings:
        settings = (
            db.query(CommissionSettings)
            .filter(
                CommissionSettings.currency == currency,
                CommissionSettings.is_active.is_(True),
            )
            .first()
        )
        if settings is None:
            raise ValueError(
                f"No active commission settings for currency {currency}"
            )
        return settings

    @staticmethod
    def get_for_deal(
        db: Session,
        deal_id: int,
    ) -> Commission | None:
        return (
            db.query(Commission)
            .filter(Commission.deal_id == deal_id)
            .first()
        )

    @staticmethod
    def calculate_platform_commission(
        *,
        deal_amount: Decimal,
        merchant_amount: Decimal | None,
        merchant_rate: Decimal | None,
        minimum_amount: Decimal,
        platform_rate: Decimal,
        currency: str,
    ) -> tuple[Decimal, bool]:
        """
        Returns:
            (final_commission, adjusted_by_platform)

        The merchant may propose either a fixed amount or a percentage.
        The platform automatically enforces the configured minimum.
        """

        if deal_amount <= Decimal("0"):
            raise ValueError("Deal amount must be greater than zero")

        if merchant_amount is not None and merchant_amount < Decimal("0"):
            raise ValueError("Merchant commission cannot be negative")

        if merchant_rate is not None and merchant_rate < Decimal("0"):
            raise ValueError("Merchant commission rate cannot be negative")

        if merchant_amount is not None:
            proposed = merchant_amount
        elif merchant_rate is not None:
            proposed = (
                deal_amount * merchant_rate / Decimal("100")
            )
        else:
            proposed = Decimal("0")

        effective_minimum = (
            Decimal("0") if minimum_amount is None else minimum_amount
        )

        platform_required = max(
            effective_minimum,
            deal_amount * platform_rate / Decimal("100"),
        )

        if proposed < platform_required:
            return platform_required, True

        return proposed, False

    @staticmethod
    def create(
        db: Session,
        *,
        deal_id: int,
        merchant_id: int,
        proposed_amount: Decimal | None,
        proposed_currency: str | None,
        proposed_rate: Decimal | None,
        platform_amount: Decimal,
        platform_rate: Decimal,
        minimum_amount: Decimal | None,
        final_amount: Decimal,
        currency: str,
        adjusted_by_platform: bool,
    ) -> Commission:

        existing = CommissionService.get_for_deal(db, deal_id)

        if existing is not None:
            raise ValueError(
                "Commission already exists for this deal"
            )

        commission = Commission(
            deal_id=deal_id,
            merchant_id=merchant_id,
            proposed_amount=proposed_amount,
            proposed_currency=proposed_currency,
            proposed_rate=proposed_rate,
            platform_amount=platform_amount,
            platform_rate=platform_rate,
            minimum_amount=minimum_amount,
            final_amount=final_amount,
            currency=currency,
            adjusted_by_platform=adjusted_by_platform,
            merchant_accepted=False,
            status=CommissionStatus.CALCULATED,
        )

        db.add(commission)
        db.flush()

        return commission

    @staticmethod
    def accept_by_merchant(
        db: Session,
        commission: Commission,
        merchant_id: int,
    ) -> Commission:
        if commission.merchant_id != merchant_id:
            raise PermissionError(
                "Only the merchant can accept this commission"
            )

        if commission.status != CommissionStatus.CALCULATED:
            raise ValueError(
                "Only CALCULATED commissions can be accepted by the merchant"
            )

        if commission.merchant_accepted:
            raise ValueError(
                "Commission has already been accepted by the merchant"
            )

        commission.merchant_accepted = True
        db.flush()
        return commission

    @staticmethod
    def mark_due(
        db: Session,
        commission: Commission,
    ) -> Commission:
        if commission.status != CommissionStatus.CALCULATED:
            raise ValueError(
                "Only CALCULATED commissions can become DUE"
            )

        if not commission.merchant_accepted:
            raise ValueError(
                "Merchant must accept the commission before it becomes DUE"
            )

        commission.status = CommissionStatus.DUE
        db.flush()
        return commission

    @staticmethod
    def settle(
        db: Session,
        commission: Commission,
    ) -> Commission:
        if commission.status != CommissionStatus.DUE:
            raise ValueError(
                "Only DUE commissions can be settled"
            )

        from datetime import datetime, timezone

        commission.status = CommissionStatus.SETTLED
        commission.settled_at = datetime.now(timezone.utc)
        db.flush()
        return commission

    @staticmethod
    def waive(
        db: Session,
        commission: Commission,
    ) -> Commission:
        if commission.status == CommissionStatus.SETTLED:
            raise ValueError(
                "Settled commissions cannot be waived"
            )

        commission.status = CommissionStatus.WAIVED
        db.flush()
        return commission
