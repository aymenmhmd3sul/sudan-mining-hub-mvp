from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.commission import Commission, CommissionStatus


class CommissionService:

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

        platform_required = max(
            minimum_amount,
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
        platform_rate: Decimal | None,
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
            final_amount=final_amount,
            currency=currency,
            adjusted_by_platform=adjusted_by_platform,
            merchant_accepted=False,
            status=CommissionStatus.PENDING,
        )

        db.add(commission)
        db.commit()
        db.refresh(commission)

        return commission

    @staticmethod
    def accept_by_merchant(
        db: Session,
        commission: Commission,
    ) -> Commission:

        commission.merchant_accepted = True

        db.commit()
        db.refresh(commission)

        return commission

    @staticmethod
    def claim(
        db: Session,
        commission: Commission,
    ) -> Commission:

        if not commission.merchant_accepted:
            raise ValueError(
                "Merchant acceptance is required before claiming commission"
            )

        commission.status = CommissionStatus.CLAIMED

        db.commit()
        db.refresh(commission)

        return commission

    @staticmethod
    def mark_paid(
        db: Session,
        commission: Commission,
    ) -> Commission:

        if commission.status != CommissionStatus.CLAIMED:
            raise ValueError(
                "Commission must be claimed before payment"
            )

        commission.status = CommissionStatus.PAID

        db.commit()
        db.refresh(commission)

        return commission
