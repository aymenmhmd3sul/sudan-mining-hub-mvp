from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.commission_tier import CommissionTier


class CommissionTierService:

    @staticmethod
    def list_active(
        db: Session,
        currency: str,
    ) -> list[CommissionTier]:
        return (
            db.query(CommissionTier)
            .filter(
                CommissionTier.currency == currency.upper(),
                CommissionTier.is_active.is_(True),
            )
            .order_by(
                CommissionTier.max_amount.is_(None),
                CommissionTier.max_amount.asc(),
                CommissionTier.id.asc(),
            )
            .all()
        )

    @staticmethod
    def get_for_amount(
        db: Session,
        currency: str,
        amount: Decimal,
    ) -> CommissionTier | None:
        currency = currency.upper()

        tiers = (
            db.query(CommissionTier)
            .filter(
                CommissionTier.currency == currency,
                CommissionTier.is_active.is_(True),
            )
            .order_by(
                CommissionTier.max_amount.is_(None),
                CommissionTier.max_amount.asc(),
                CommissionTier.id.asc(),
            )
            .all()
        )

        for tier in tiers:
            if tier.max_amount is None:
                return tier

            if amount <= Decimal(str(tier.max_amount)):
                return tier

        return None

    @staticmethod
    def validate(
        db: Session,
        currency: str,
        tiers: list[dict],
    ) -> None:
        currency = currency.upper()

        if not tiers:
            raise ValueError(f"No commission tiers supplied for {currency}")

        normalized = []
        final_count = 0
        previous_max = Decimal("0")

        for item in tiers:
            max_amount = item.get("max_amount")
            rate = Decimal(str(item["commission_rate"]))
            minimum = Decimal(str(item.get("minimum_amount", "0")))

            if rate < 0 or rate > 100:
                raise ValueError("Commission rate must be between 0 and 100")

            if minimum < 0:
                raise ValueError("Minimum commission amount cannot be negative")

            if max_amount is None:
                final_count += 1
            else:
                max_amount = Decimal(str(max_amount))

                if max_amount <= 0:
                    raise ValueError("Tier max_amount must be greater than zero")

                if max_amount <= previous_max:
                    raise ValueError(
                        "Commission tier max_amount values must be strictly increasing"
                    )

                previous_max = max_amount

            normalized.append(
                {
                    "max_amount": max_amount,
                    "commission_rate": rate,
                    "minimum_amount": minimum,
                }
            )

        if final_count != 1:
            raise ValueError(
                "Commission tiers require exactly one final tier with max_amount=null"
            )

        if normalized[-1]["max_amount"] is not None:
            raise ValueError(
                "The final commission tier must have max_amount=null"
            )

    @staticmethod
    def replace_active(
        db: Session,
        currency: str,
        tiers: list[dict],
    ) -> list[CommissionTier]:
        currency = currency.upper()

        CommissionTierService.validate(db, currency, tiers)

        (
            db.query(CommissionTier)
            .filter(
                CommissionTier.currency == currency,
                CommissionTier.is_active.is_(True),
            )
            .update(
                {"is_active": False},
                synchronize_session=False,
            )
        )

        created = []

        for item in tiers:
            tier = CommissionTier(
                currency=currency,
                max_amount=item.get("max_amount"),
                commission_rate=Decimal(str(item["commission_rate"])),
                minimum_amount=Decimal(str(item.get("minimum_amount", "0"))),
                is_active=True,
            )
            db.add(tier)
            created.append(tier)

        db.flush()
        return created
