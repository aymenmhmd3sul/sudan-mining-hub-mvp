from sqlalchemy.orm import Session

from app.models.buyer_request import BuyerRequest, RequestStatus


class RequestService:
    @staticmethod
    def get_by_id(db: Session, request_id: int) -> BuyerRequest | None:
        return (
            db.query(BuyerRequest)
            .filter(BuyerRequest.id == request_id)
            .first()
        )

    @staticmethod
    def list_open(db: Session, limit: int = 100) -> list[BuyerRequest]:
        return (
            db.query(BuyerRequest)
            .filter(BuyerRequest.status == RequestStatus.OPEN)
            .order_by(BuyerRequest.id.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def create(db: Session, **data) -> BuyerRequest:
        request = BuyerRequest(**data)
        db.add(request)
        db.commit()
        db.refresh(request)
        return request
