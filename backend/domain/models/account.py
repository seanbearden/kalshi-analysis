"""Database models for account integration."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class UserCredential(Base):
    """User API credentials stored with encryption.

    Stores Kalshi API keys with Fernet encryption for secure credential management.
    For Phase 1, user_id is always "default" (single-user deployment).
    """

    __tablename__ = "user_credentials"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default="gen_random_uuid()",
    )
    user_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default="now()",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default="now()",
        onupdate=lambda: datetime.now(UTC),
    )

    def __repr__(self) -> str:
        return f"<UserCredential(user_id='{self.user_id}', created={self.created_at})>"


class PositionCache(Base):
    """Cached position data for offline mode and reconciliation.

    Write-through cache pattern: positions written to both memory (PositionTracker)
    and database (PositionCache) to survive backend restarts and enable reconciliation.
    """

    __tablename__ = "position_cache"
    __table_args__ = (
        UniqueConstraint("user_id", "ticker", name="uq_user_ticker"),
        CheckConstraint("side IN ('YES', 'NO')", name="ck_position_side"),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default="gen_random_uuid()",
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(50), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)  # 'YES' or 'NO'
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_entry_price: Mapped[int] = mapped_column(Integer, nullable=False, comment="Price in cents")
    current_price: Mapped[int] = mapped_column(Integer, nullable=False, comment="Price in cents")
    entry_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        server_default="now()",
    )

    def __repr__(self) -> str:
        return f"<PositionCache(ticker='{self.ticker}', side='{self.side}', qty={self.quantity})>"
