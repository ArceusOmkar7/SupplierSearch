"""Conversation history; model text is a draft interpretation and never a confirmation."""

from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, CreatedAt, UUIDPrimaryKey


class ConversationMessage(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        UniqueConstraint("case_id", "id"),
        UniqueConstraint("case_id", "sequence"),
        UniqueConstraint("case_id", "client_message_id"),
        ForeignKeyConstraint(
            ["case_id", "revision_id"],
            ["requirement_revisions.case_id", "requirement_revisions.id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("sequence > 0", name="positive_sequence"),
        CheckConstraint("actor IN ('buyer','assistant','system')", name="actor"),
    )

    case_id: Mapped[UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    revision_id: Mapped[UUID | None]
    actor: Mapped[str]
    text: Mapped[str]
    component_refs: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    sequence: Mapped[int]
    client_message_id: Mapped[str | None]
