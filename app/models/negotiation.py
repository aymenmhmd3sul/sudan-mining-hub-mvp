import enum

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.sql import func

from sqlalchemy.orm import relationship
from app.db.session import Base


class NegotiationStatus(str, enum.Enum):
    OPEN = "OPEN"
    AGREED = "AGREED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


class NegotiationRoom(Base):
    __tablename__ = "negotiation_rooms"

    id = Column(Integer, primary_key=True, index=True)

    request_id = Column(
        Integer,
        ForeignKey(
            "buyer_requests.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    offer_id = Column(
        Integer,
        ForeignKey(
            "offers.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    status = Column(
        SQLEnum(NegotiationStatus),
        nullable=False,
        default=NegotiationStatus.OPEN,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    request = relationship(
        "BuyerRequest",
        back_populates="negotiation_rooms",
        foreign_keys="NegotiationRoom.request_id",
    )

    offer = relationship(
        "Offer",
        back_populates="negotiation_rooms",
        foreign_keys="NegotiationRoom.offer_id",
    )

    participants = relationship(
        "NegotiationParticipant",
        back_populates="room",
        foreign_keys="NegotiationParticipant.room_id",
        cascade="all, delete-orphan",
    )

    messages = relationship(
        "NegotiationMessage",
        back_populates="room",
        foreign_keys="NegotiationMessage.room_id",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_negotiation_rooms_request_status",
            request_id,
            status,
        ),
    )


class NegotiationParticipant(Base):
    __tablename__ = "negotiation_participants"

    id = Column(Integer, primary_key=True, index=True)

    room_id = Column(
        Integer,
        ForeignKey(
            "negotiation_rooms.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    room = relationship(
        "NegotiationRoom",
        back_populates="participants",
        foreign_keys="NegotiationParticipant.room_id",
    )

    user = relationship(
        "UserModel",
        back_populates="negotiation_participants",
        foreign_keys="NegotiationParticipant.user_id",
    )

    joined_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_negotiation_participants_room_user",
            room_id,
            user_id,
            unique=True,
        ),
    )


class NegotiationMessage(Base):
    __tablename__ = "negotiation_messages"

    id = Column(Integer, primary_key=True, index=True)

    room_id = Column(
        Integer,
        ForeignKey(
            "negotiation_rooms.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    sender_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    body = Column(
        Text,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    room = relationship(
        "NegotiationRoom",
        back_populates="messages",
        foreign_keys="NegotiationMessage.room_id",
    )

    sender = relationship(
        "UserModel",
        back_populates="negotiation_messages",
        foreign_keys="NegotiationMessage.sender_id",
    )

    __table_args__ = (
        Index(
            "ix_negotiation_messages_room_created",
            room_id,
            created_at,
        ),
    )
