from app.models.deal import Deal, DealStatus
from app.models.user import UserModel, UserRole


class DealAccessService:
    """Centralized access rules for sensitive deal-party information."""

    DISCLOSURE_STATUSES = {
        DealStatus.CONFIRMED,
        DealStatus.DELIVERED,
        DealStatus.COMPLETED,
    }

    @staticmethod
    def can_view_deal(user: UserModel, deal: Deal) -> bool:
        if user.role == UserRole.ADMIN:
            return True

        return user.id in {
            deal.buyer_id,
            deal.merchant_id,
            deal.agent_id,
        }

    @staticmethod
    def can_view_contacts(user: UserModel, deal: Deal) -> bool:
        if user.role == UserRole.ADMIN:
            return True

        if deal.status not in DealAccessService.DISCLOSURE_STATUSES:
            return False

        return user.id in {
            deal.buyer_id,
            deal.merchant_id,
            deal.agent_id,
        }

    @staticmethod
    def require_contact_access(user: UserModel, deal: Deal) -> None:
        if not DealAccessService.can_view_contacts(user, deal):
            raise PermissionError("Deal contact access denied")
