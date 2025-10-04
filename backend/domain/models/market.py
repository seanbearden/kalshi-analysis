"""Market domain models."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class DataSource(str, Enum):
    """Source of market data."""

    POLL = "poll"  # Phase 1: REST API polling
    WEBSOCKET = "websocket"  # Phase 2: Real-time WebSocket
    BACKFILL = "backfill"  # Historical data backfill


class MarketSnapshot(Base):
    """Market snapshot at a point in time.

    Captures market state including prices, volume, and metadata.
    Enhanced for Phase 2 WebSocket support with source tracking and sequence numbers.

    Attributes:
        id: Unique snapshot identifier
        ticker: Kalshi market ticker (e.g., "INXD-24FEB16-T4125")
        timestamp: When snapshot was captured (timezone-aware)
        source: Where data came from (poll/websocket/backfill)
        sequence: WebSocket sequence number for gap detection (null for polling)
        yes_price: Current YES price in cents
        no_price: Current NO price in cents
        volume: Total volume traded
        raw_data: Complete API response for audit/debug
        created_at: Database record creation time
    """

    __tablename__ = "market_snapshots"

    # Primary key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Core fields
    ticker: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        index=True, nullable=False
    )  # PostgreSQL TIMESTAMPTZ
    source: Mapped[DataSource] = mapped_column(index=True, nullable=False)
    sequence: Mapped[int | None] = mapped_column(nullable=True)  # WebSocket only

    # Market data
    yes_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    no_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    volume: Mapped[int] = mapped_column(nullable=False)

    # Audit trail
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    __table_args__ = (
        # Composite index for time-series queries
        Index("ix_ticker_timestamp", "ticker", "timestamp"),
        # Unique constraint for WebSocket deduplication
        Index(
            "ix_ticker_source_sequence",
            "ticker",
            "source",
            "sequence",
            unique=True,
            postgresql_where=(source == DataSource.WEBSOCKET),
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MarketSnapshot(ticker={self.ticker}, "
            f"timestamp={self.timestamp}, source={self.source.value})>"
        )
