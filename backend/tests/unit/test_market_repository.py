"""Unit tests for MarketRepository."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from domain.models.market import DataSource
from domain.repositories import MarketRepository


class TestMarketRepository:
    """Test suite for MarketRepository."""

    async def test_create_snapshot(self, market_repository: MarketRepository) -> None:
        """Test creating a market snapshot."""
        snapshot = await market_repository.create_snapshot(
            ticker="TEST-001",
            timestamp=datetime.now(UTC),
            source=DataSource.POLL,
            yes_price=60.0,
            no_price=40.0,
            volume=1000,
            raw_data={"test": "data"},
        )

        assert snapshot.id is not None
        assert snapshot.ticker == "TEST-001"
        assert snapshot.yes_price == Decimal("60.0")
        assert snapshot.no_price == Decimal("40.0")
        assert snapshot.volume == 1000
        assert snapshot.source == DataSource.POLL

    async def test_get_by_ticker(self, market_repository: MarketRepository) -> None:
        """Test retrieving snapshots by ticker."""
        # Create multiple snapshots for same ticker
        ticker = "TICKER-001"
        now = datetime.now(UTC)

        for i in range(3):
            await market_repository.create_snapshot(
                ticker=ticker,
                timestamp=now - timedelta(hours=i),
                source=DataSource.POLL,
                yes_price=50.0 + i,
                no_price=50.0 - i,
                volume=1000 * (i + 1),
                raw_data={},
            )

        # Retrieve snapshots
        snapshots = await market_repository.get_by_ticker(ticker)

        assert len(snapshots) == 3
        # Should be ordered by timestamp descending
        assert snapshots[0].timestamp > snapshots[1].timestamp
        assert snapshots[1].timestamp > snapshots[2].timestamp

    async def test_get_by_ticker_with_pagination(self, market_repository: MarketRepository) -> None:
        """Test pagination for ticker snapshots."""
        ticker = "TICKER-002"
        now = datetime.now(UTC)

        # Create 5 snapshots
        for i in range(5):
            await market_repository.create_snapshot(
                ticker=ticker,
                timestamp=now - timedelta(hours=i),
                source=DataSource.POLL,
                yes_price=50.0,
                no_price=50.0,
                volume=1000,
                raw_data={},
            )

        # Get first 2
        page1 = await market_repository.get_by_ticker(ticker, skip=0, limit=2)
        assert len(page1) == 2

        # Get next 2
        page2 = await market_repository.get_by_ticker(ticker, skip=2, limit=2)
        assert len(page2) == 2

        # Ensure different results
        assert page1[0].id != page2[0].id

    async def test_get_latest_by_ticker(self, market_repository: MarketRepository) -> None:
        """Test retrieving latest snapshot for a ticker."""
        ticker = "TICKER-003"
        now = datetime.now(UTC)

        # Create snapshots at different times
        await market_repository.create_snapshot(
            ticker=ticker,
            timestamp=now - timedelta(hours=2),
            source=DataSource.POLL,
            yes_price=45.0,
            no_price=55.0,
            volume=1000,
            raw_data={},
        )

        latest_snapshot = await market_repository.create_snapshot(
            ticker=ticker,
            timestamp=now,
            source=DataSource.POLL,
            yes_price=60.0,
            no_price=40.0,
            volume=2000,
            raw_data={},
        )

        # Get latest
        result = await market_repository.get_latest_by_ticker(ticker)

        assert result is not None
        assert result.id == latest_snapshot.id
        assert result.yes_price == Decimal("60.0")
        assert result.volume == 2000

    async def test_get_latest_by_ticker_not_found(
        self, market_repository: MarketRepository
    ) -> None:
        """Test getting latest snapshot for non-existent ticker."""
        result = await market_repository.get_latest_by_ticker("NONEXISTENT")
        assert result is None

    async def test_get_all_latest(self, market_repository: MarketRepository) -> None:
        """Test retrieving latest snapshot for each ticker."""
        now = datetime.now(UTC)

        # Create snapshots for multiple tickers
        for ticker_num in range(3):
            ticker = f"TICKER-{ticker_num:03d}"
            for time_offset in range(2):
                await market_repository.create_snapshot(
                    ticker=ticker,
                    timestamp=now - timedelta(hours=time_offset),
                    source=DataSource.POLL,
                    yes_price=50.0 + time_offset,
                    no_price=50.0 - time_offset,
                    volume=1000,
                    raw_data={},
                )

        # Get latest for all tickers
        latest_snapshots = await market_repository.get_all_latest()

        assert len(latest_snapshots) == 3
        # Each should be the most recent for its ticker
        tickers = {s.ticker for s in latest_snapshots}
        assert len(tickers) == 3  # All unique tickers

    async def test_get_by_time_range(self, market_repository: MarketRepository) -> None:
        """Test retrieving snapshots within time range."""
        ticker = "TICKER-004"
        base_time = datetime.now(UTC)

        # Create snapshots over 6 hours
        for i in range(6):
            await market_repository.create_snapshot(
                ticker=ticker,
                timestamp=base_time - timedelta(hours=i),
                source=DataSource.POLL,
                yes_price=50.0,
                no_price=50.0,
                volume=1000,
                raw_data={},
            )

        # Query for middle 3 hours
        start = base_time - timedelta(hours=4)
        end = base_time - timedelta(hours=1)

        snapshots = await market_repository.get_by_time_range(ticker, start, end)

        assert len(snapshots) == 4  # Hours 1, 2, 3, 4 (inclusive)
        # Should be ordered by timestamp ascending
        assert all(
            snapshots[i].timestamp <= snapshots[i + 1].timestamp for i in range(len(snapshots) - 1)
        )

    async def test_get_by_source(self, market_repository: MarketRepository) -> None:
        """Test retrieving snapshots by data source."""
        now = datetime.now(UTC)

        # Create snapshots with different sources
        await market_repository.create_snapshot(
            ticker="TICKER-005",
            timestamp=now,
            source=DataSource.POLL,
            yes_price=50.0,
            no_price=50.0,
            volume=1000,
            raw_data={},
        )

        await market_repository.create_snapshot(
            ticker="TICKER-006",
            timestamp=now,
            source=DataSource.WEBSOCKET,
            yes_price=55.0,
            no_price=45.0,
            volume=2000,
            raw_data={},
        )

        await market_repository.create_snapshot(
            ticker="TICKER-007",
            timestamp=now,
            source=DataSource.BACKFILL,
            yes_price=60.0,
            no_price=40.0,
            volume=3000,
            raw_data={},
        )

        # Query by source
        poll_snapshots = await market_repository.get_by_source(DataSource.POLL)
        assert len(poll_snapshots) == 1
        assert poll_snapshots[0].source == DataSource.POLL

        ws_snapshots = await market_repository.get_by_source(DataSource.WEBSOCKET)
        assert len(ws_snapshots) == 1
        assert ws_snapshots[0].source == DataSource.WEBSOCKET

    async def test_create_snapshot_with_sequence(self, market_repository: MarketRepository) -> None:
        """Test creating snapshot with WebSocket sequence number."""
        snapshot = await market_repository.create_snapshot(
            ticker="WS-TICKER",
            timestamp=datetime.now(UTC),
            source=DataSource.WEBSOCKET,
            yes_price=50.0,
            no_price=50.0,
            volume=1000,
            raw_data={},
            sequence=12345,
        )

        assert snapshot.sequence == 12345
        assert snapshot.source == DataSource.WEBSOCKET
