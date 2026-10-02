"""SQLAlchemy ORM models for Users, Conversations, Messages, and Advisory Records."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.app.db.base import Base


def generate_uuid() -> str:
    """Generate a clean UUID string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """User account model for authentication and data ownership."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationship to user's conversations
    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Conversation.updated_at)",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class Conversation(Base):
    """Conversation thread isolating messages and advisory records per user."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title = Column(String(255), default="New Conversation", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    advisories = relationship(
        "AdvisoryRecord",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="AdvisoryRecord.created_at",
    )

    __table_args__ = (
        Index("idx_conversation_user_updated", "user_id", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} user_id={self.user_id} title={self.title}>"


class Message(Base):
    """Individual conversation message turn (user or assistant)."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role} conv={self.conversation_id}>"


class AdvisoryRecord(Base):
    """Structured audit trail of safety policy decisions and factual weather conditions."""

    __tablename__ = "advisory_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_query = Column(Text, nullable=False)
    location = Column(String(255), nullable=True)
    resolved_location_name = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    weather_metrics = Column(JSON, nullable=True)
    activity = Column(String(100), nullable=True)
    person_context = Column(String(100), nullable=True)
    selected_sop = Column(JSON, nullable=True)
    matched_sops = Column(JSON, nullable=True)
    severity = Column(String(20), nullable=True)
    generated_response = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="advisories")

    def __repr__(self) -> str:
        return f"<AdvisoryRecord id={self.id} sop={self.selected_sop.get('id') if self.selected_sop else None}>"
