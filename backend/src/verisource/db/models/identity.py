"""Operator-provisioned buyers and hashed opaque sessions; restored sessions are discarded."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from verisource.db.base import Base, CreatedAt, UUIDPrimaryKey


class BuyerAccount(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "buyer_accounts"

    username_normalized: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    display_name: Mapped[str]
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LoginSession(CreatedAt, Base):
    __tablename__ = "login_sessions"
    __table_args__ = (
        CheckConstraint("expires_at > created_at", name="positive_lifetime"),
        CheckConstraint("last_seen_at >= created_at", name="valid_last_seen"),
    )

    id_hash: Mapped[str] = mapped_column(primary_key=True)
    buyer_id: Mapped[UUID] = mapped_column(ForeignKey("buyer_accounts.id"), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    csrf_secret: Mapped[str]
