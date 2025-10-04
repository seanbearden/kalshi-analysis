"""Market repository with domain-specific queries."""

from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models import DataSource, MarketSnapshot
from domain.repositories.base import BaseRepository


class MarketRepository(BaseRepository[MarketSnapshot]):
    """Repository for market snapshot operations."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(MarketSnapshot, session)

    async def get_by_ticker(
        self, ticker: str, skip: int = 0, limit: int = 100
    ) -> list[MarketSnapshot]:
        """Get all snapshots for a ticker, ordered by timestamp descending.

        Args:
            ticker: Market ticker
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of snapshots for the ticker
        """
        stmt = (
            select(MarketSnapshot)
            .where(MarketSnapshot.ticker == ticker)
            .order_by(desc(MarketSnapshot.timestamp))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_latest(self, skip: int = 0, limit: int = 100) -> list[MarketSnapshot]:
        """Get latest snapshot for each unique ticker.

        Args:
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of latest snapshots for each ticker
        """
        # Subquery to get latest timestamp for each ticker
        from sqlalchemy import func

        latest_timestamps = (
            select(
                MarketSnapshot.ticker,
                func.max(MarketSnapshot.timestamp).label("max_timestamp"),
            )
            .group_by(MarketSnapshot.ticker)
            .subquery()
        )

        # Get the actual snapshots
        stmt = (
            select(MarketSnapshot)
            .join(
                latest_timestamps,
                (MarketSnapshot.ticker == latest_timestamps.c.ticker)
                & (MarketSnapshot.timestamp == latest_timestamps.c.max_timestamp),
            )
            .order_by(desc(MarketSnapshot.timestamp))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_by_ticker(self, ticker: str) -> MarketSnapshot | None:
        """Get most recent snapshot for a ticker.

        Args:
            ticker: Market ticker

        Returns:
            Latest snapshot or None
        """
        stmt = (
            select(MarketSnapshot)
            .where(MarketSnapshot.ticker == ticker)
            .order_by(desc(MarketSnapshot.timestamp))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_time_range(
        self,
        ticker: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[MarketSnapshot]:
        """Get snapshots for ticker within time range.

        Args:
            ticker: Market ticker
            start_time: Range start (inclusive)
            end_time: Range end (inclusive)

        Returns:
            Snapshots within range, ordered by timestamp
        """
        stmt = (
            select(MarketSnapshot)
            .where(
                MarketSnapshot.ticker == ticker,
                MarketSnapshot.timestamp >= start_time,
                MarketSnapshot.timestamp <= end_time,
            )
            .order_by(MarketSnapshot.timestamp)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_source(
        self, source: DataSource, skip: int = 0, limit: int = 100
    ) -> list[MarketSnapshot]:
        """Get snapshots by data source.

        Args:
            source: Data source (poll/websocket/backfill)
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Snapshots from the specified source
        """
        stmt = (
            select(MarketSnapshot)
            .where(MarketSnapshot.source == source)
            .order_by(desc(MarketSnapshot.timestamp))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_snapshot(
        self,
        ticker: str,
        timestamp: datetime,
        source: DataSource,
        yes_price: float,
        no_price: float,
        volume: int,
        raw_data: dict[str, Any],
        sequence: int | None = None,
    ) -> MarketSnapshot:
        """Create market snapshot with validation.

        Args:
            ticker: Market ticker
            timestamp: Snapshot timestamp
            source: Data source
            yes_price: YES price in cents
            no_price: NO price in cents
            volume: Total volume
            raw_data: Complete API response
            sequence: WebSocket sequence number (optional)

        Returns:
            Created snapshot
        """
        return await self.create(
            ticker=ticker,
            timestamp=timestamp,
            source=source,
            yes_price=yes_price,
            no_price=no_price,
            volume=volume,
            raw_data=raw_data,
            sequence=sequence,
        )

    async def detect_gaps(self, ticker: str) -> list[int]:
        """Detect missing WebSocket sequence numbers for a ticker.

        Phase 2 feature: Gap detection enables data integrity monitoring
        and backfill triggering.

        Args:
            ticker: Market ticker to check for gaps

        Returns:
            List of missing sequence numbers (empty if no gaps)

        Example:
            If sequences are [1, 2, 4, 5, 7], returns [3, 6]
        """
        # Get all WebSocket sequences for this ticker, ordered
        stmt = (
            select(MarketSnapshot.sequence)
            .where(
                MarketSnapshot.ticker == ticker,
                MarketSnapshot.source == DataSource.WEBSOCKET,
                MarketSnapshot.sequence.isnot(None),
            )
            .order_by(MarketSnapshot.sequence)
        )
        result = await self.session.execute(stmt)
        sequences = [row[0] for row in result.all()]

        # No sequences or only one sequence means no gaps
        if len(sequences) < 2:
            return []

        # Find gaps in sequence numbers
        gaps = []
        min_seq = sequences[0]
        max_seq = sequences[-1]

        # Check for missing numbers in the range
        sequence_set = set(sequences)
        for seq in range(min_seq, max_seq + 1):
            if seq not in sequence_set:
                gaps.append(seq)

        return gaps

    async def get_websocket_snapshots_by_sequence(
        self, ticker: str, min_seq: int, max_seq: int
    ) -> list[MarketSnapshot]:
        """Get WebSocket snapshots within a sequence range.

        Used for gap analysis and debugging.

        Args:
            ticker: Market ticker
            min_seq: Minimum sequence number (inclusive)
            max_seq: Maximum sequence number (inclusive)

        Returns:
            WebSocket snapshots within sequence range
        """
        stmt = (
            select(MarketSnapshot)
            .where(
                MarketSnapshot.ticker == ticker,
                MarketSnapshot.source == DataSource.WEBSOCKET,
                MarketSnapshot.sequence >= min_seq,
                MarketSnapshot.sequence <= max_seq,
            )
            .order_by(MarketSnapshot.sequence)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
