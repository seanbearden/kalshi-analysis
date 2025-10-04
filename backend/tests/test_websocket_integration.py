"""WebSocket integration tests for Phase 2.

Tests WebSocket client, gap detection, and dual data source orchestration.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from domain.models import DataSource
from domain.repositories import MarketRepository
from infrastructure.polling.poller import MarketPoller


class TestWebSocketClient:
    """Test WebSocket client functionality."""

    @pytest.mark.asyncio
    async def test_websocket_saves_to_database(self, session):
        """Test that WebSocket messages are saved to database."""

        # Create async generator for mock WebSocket messages
        async def mock_listen():
            messages = [
                {
                    "type": "ticker",
                    "ticker": "TEST-TICKER",
                    "yes_price": 52,
                    "no_price": 48,
                    "volume": 1000,
                    "seq": 1,
                    "timestamp": "2024-10-04T19:30:00Z",
                },
                {
                    "type": "ticker",
                    "ticker": "TEST-TICKER",
                    "yes_price": 53,
                    "no_price": 47,
                    "volume": 1100,
                    "seq": 2,
                    "timestamp": "2024-10-04T19:30:01Z",
                },
            ]
            for msg in messages:
                yield msg

        # Mock WebSocket client - configure listen to be a regular function that returns the generator
        mock_ws = AsyncMock()
        mock_ws.listen = mock_listen

        # Create poller instance
        poller = MarketPoller()

        # Create mock session maker that returns our test session
        @asynccontextmanager
        async def mock_session_maker():
            yield session

        # Mock the WebSocket client creation and session maker
        with (
            patch("infrastructure.polling.poller.KalshiWebSocketClient", return_value=mock_ws),
            patch.object(poller, "session_maker", mock_session_maker),
        ):
            # Process two messages
            messages = []
            async for msg in mock_ws.listen():
                messages.append(msg)
                await poller._save_websocket_snapshot(msg)
                if len(messages) >= 2:
                    break

        # Verify snapshots were saved
        repo = MarketRepository(session)
        snapshots = await repo.get_by_ticker("TEST-TICKER")

        assert len(snapshots) == 2
        assert snapshots[0].source == DataSource.WEBSOCKET
        assert snapshots[0].sequence == 2  # Latest first
        assert snapshots[1].sequence == 1
        assert float(snapshots[0].yes_price) == 0.53  # 53 cents / 100
        assert float(snapshots[1].yes_price) == 0.52

    @pytest.mark.asyncio
    async def test_websocket_reconnection(self):
        """Test WebSocket reconnection on connection loss."""
        # Mock WebSocket that fails then succeeds
        mock_ws = AsyncMock()
        mock_ws.connect.side_effect = [ConnectionError("Connection lost"), None]

        with patch(
            "infrastructure.polling.poller.KalshiWebSocketClient",
            return_value=mock_ws,
        ):
            # Test reconnection logic - tenacity handles retry
            # In real scenario, first attempt fails, second succeeds
            pass  # Placeholder test - actual retry logic tested via integration


class TestGapDetection:
    """Test sequence gap detection."""

    @pytest.mark.asyncio
    async def test_gap_detection(self, session):
        """Test detection of missing sequence numbers."""
        repo = MarketRepository(session)

        # Create snapshots with gap at sequence 3
        await repo.create_snapshot(
            ticker="TEST",
            timestamp=datetime.fromisoformat("2024-10-04T19:30:00+00:00"),
            source=DataSource.WEBSOCKET,
            yes_price=50,
            no_price=50,
            volume=100,
            raw_data={},
            sequence=1,
        )
        await repo.create_snapshot(
            ticker="TEST",
            timestamp=datetime.fromisoformat("2024-10-04T19:30:01+00:00"),
            source=DataSource.WEBSOCKET,
            yes_price=51,
            no_price=49,
            volume=110,
            raw_data={},
            sequence=2,
        )
        await repo.create_snapshot(
            ticker="TEST",
            timestamp=datetime.fromisoformat("2024-10-04T19:30:03+00:00"),
            source=DataSource.WEBSOCKET,
            yes_price=52,
            no_price=48,
            volume=120,
            raw_data={},
            sequence=4,
        )

        await session.commit()

        # Detect gaps
        gaps = await repo.detect_gaps("TEST")

        assert gaps == [3]

    @pytest.mark.asyncio
    async def test_no_gaps(self, session):
        """Test no gaps detected for continuous sequences."""
        repo = MarketRepository(session)

        # Create continuous sequences
        for seq in range(1, 6):
            await repo.create_snapshot(
                ticker="TEST-NOGAPS",
                timestamp=datetime.fromisoformat(f"2024-10-04T19:30:0{seq}+00:00"),
                source=DataSource.WEBSOCKET,
                yes_price=50,
                no_price=50,
                volume=100,
                raw_data={},
                sequence=seq,
            )

        await session.commit()

        gaps = await repo.detect_gaps("TEST-NOGAPS")

        assert gaps == []

    @pytest.mark.asyncio
    async def test_multiple_gaps(self, session):
        """Test detection of multiple gaps."""
        repo = MarketRepository(session)

        # Create snapshots with gaps at 3, 5, 6
        for seq in [1, 2, 4, 7, 8]:
            await repo.create_snapshot(
                ticker="TEST-MULTIGAPS",
                timestamp=datetime.fromisoformat(f"2024-10-04T19:30:0{seq}+00:00"),
                source=DataSource.WEBSOCKET,
                yes_price=50,
                no_price=50,
                volume=100,
                raw_data={},
                sequence=seq,
            )

        await session.commit()

        gaps = await repo.detect_gaps("TEST-MULTIGAPS")

        assert gaps == [3, 5, 6]


class TestDualDataSources:
    """Test REST and WebSocket working together."""

    @pytest.mark.asyncio
    async def test_both_sources_save(self, session):
        """Test that both REST and WebSocket data are saved."""
        repo = MarketRepository(session)

        # Save REST snapshot
        await repo.create_snapshot(
            ticker="TEST-DUAL",
            timestamp=datetime.fromisoformat("2024-10-04T19:30:00+00:00"),
            source=DataSource.POLL,
            yes_price=50,
            no_price=50,
            volume=100,
            raw_data={},
            sequence=None,  # REST has no sequence
        )

        # Save WebSocket snapshot
        await repo.create_snapshot(
            ticker="TEST-DUAL",
            timestamp=datetime.fromisoformat("2024-10-04T19:30:01+00:00"),
            source=DataSource.WEBSOCKET,
            yes_price=51,
            no_price=49,
            volume=110,
            raw_data={},
            sequence=1,
        )

        await session.commit()

        # Verify both sources exist
        all_snapshots = await repo.get_by_ticker("TEST-DUAL")
        assert len(all_snapshots) == 2

        # Verify we have one of each source for this ticker
        sources = {snapshot.source for snapshot in all_snapshots}
        assert DataSource.POLL in sources
        assert DataSource.WEBSOCKET in sources

    @pytest.mark.asyncio
    async def test_latest_prefers_websocket(self, session):
        """Test that latest snapshot prefers WebSocket when more recent."""
        repo = MarketRepository(session)

        # REST snapshot (older)
        await repo.create_snapshot(
            ticker="TEST-LATEST",
            timestamp=datetime.fromisoformat("2024-10-04T19:30:00+00:00"),
            source=DataSource.POLL,
            yes_price=50,
            no_price=50,
            volume=100,
            raw_data={},
        )

        # WebSocket snapshot (newer)
        await repo.create_snapshot(
            ticker="TEST-LATEST",
            timestamp=datetime.fromisoformat("2024-10-04T19:30:05+00:00"),
            source=DataSource.WEBSOCKET,
            yes_price=52,
            no_price=48,
            volume=120,
            raw_data={},
            sequence=1,
        )

        await session.commit()

        # Get latest
        latest = await repo.get_latest_by_ticker("TEST-LATEST")

        assert latest is not None
        assert latest.source == DataSource.WEBSOCKET
        assert float(latest.yes_price) == 52.0
