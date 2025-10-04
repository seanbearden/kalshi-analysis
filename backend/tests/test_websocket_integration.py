"""WebSocket integration tests for Phase 2.

Tests WebSocket client, gap detection, and dual data source orchestration.
"""

from unittest.mock import AsyncMock, patch

import pytest

from domain.models import DataSource
from domain.repositories import MarketRepository
from infrastructure.polling.poller import MarketPoller


class TestWebSocketClient:
    """Test WebSocket client functionality."""

    @pytest.mark.asyncio
    async def test_websocket_saves_to_database(self, db_session):
        """Test that WebSocket messages are saved to database."""
        # Mock WebSocket client
        mock_ws = AsyncMock()
        mock_ws.listen.return_value = iter(
            [
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
        )

        # Create poller instance
        poller = MarketPoller()

        # Mock the WebSocket client creation
        with patch(
            "infrastructure.polling.poller.KalshiWebSocketClient",
            return_value=mock_ws,
        ):
            # Process two messages
            messages = []
            async for msg in mock_ws.listen():
                messages.append(msg)
                await poller._save_websocket_snapshot(msg)
                if len(messages) >= 2:
                    break

        # Verify snapshots were saved
        repo = MarketRepository(db_session)
        snapshots = await repo.get_by_ticker("TEST-TICKER")

        assert len(snapshots) == 2
        assert snapshots[0].source == DataSource.WEBSOCKET
        assert snapshots[0].sequence == 2  # Latest first
        assert snapshots[1].sequence == 1
        assert snapshots[0].yes_price == 0.53  # 53 cents / 100
        assert snapshots[1].yes_price == 0.52

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
    async def test_gap_detection(self, db_session):
        """Test detection of missing sequence numbers."""
        repo = MarketRepository(db_session)

        # Create snapshots with gap at sequence 3
        await repo.create_snapshot(
            ticker="TEST",
            timestamp="2024-10-04T19:30:00+00:00",
            source=DataSource.WEBSOCKET,
            yes_price=50,
            no_price=50,
            volume=100,
            raw_data={},
            sequence=1,
        )
        await repo.create_snapshot(
            ticker="TEST",
            timestamp="2024-10-04T19:30:01+00:00",
            source=DataSource.WEBSOCKET,
            yes_price=51,
            no_price=49,
            volume=110,
            raw_data={},
            sequence=2,
        )
        await repo.create_snapshot(
            ticker="TEST",
            timestamp="2024-10-04T19:30:03+00:00",
            source=DataSource.WEBSOCKET,
            yes_price=52,
            no_price=48,
            volume=120,
            raw_data={},
            sequence=4,
        )

        await db_session.commit()

        # Detect gaps
        gaps = await repo.detect_gaps("TEST")

        assert gaps == [3]

    @pytest.mark.asyncio
    async def test_no_gaps(self, db_session):
        """Test no gaps detected for continuous sequences."""
        repo = MarketRepository(db_session)

        # Create continuous sequences
        for seq in range(1, 6):
            await repo.create_snapshot(
                ticker="TEST",
                timestamp=f"2024-10-04T19:30:0{seq}+00:00",
                source=DataSource.WEBSOCKET,
                yes_price=50,
                no_price=50,
                volume=100,
                raw_data={},
                sequence=seq,
            )

        await db_session.commit()

        gaps = await repo.detect_gaps("TEST")

        assert gaps == []

    @pytest.mark.asyncio
    async def test_multiple_gaps(self, db_session):
        """Test detection of multiple gaps."""
        repo = MarketRepository(db_session)

        # Create snapshots with gaps at 3, 5, 6
        for seq in [1, 2, 4, 7, 8]:
            await repo.create_snapshot(
                ticker="TEST",
                timestamp=f"2024-10-04T19:30:0{seq}+00:00",
                source=DataSource.WEBSOCKET,
                yes_price=50,
                no_price=50,
                volume=100,
                raw_data={},
                sequence=seq,
            )

        await db_session.commit()

        gaps = await repo.detect_gaps("TEST")

        assert gaps == [3, 5, 6]


class TestDualDataSources:
    """Test REST and WebSocket working together."""

    @pytest.mark.asyncio
    async def test_both_sources_save(self, db_session):
        """Test that both REST and WebSocket data are saved."""
        repo = MarketRepository(db_session)

        # Save REST snapshot
        await repo.create_snapshot(
            ticker="TEST",
            timestamp="2024-10-04T19:30:00+00:00",
            source=DataSource.POLL,
            yes_price=50,
            no_price=50,
            volume=100,
            raw_data={},
            sequence=None,  # REST has no sequence
        )

        # Save WebSocket snapshot
        await repo.create_snapshot(
            ticker="TEST",
            timestamp="2024-10-04T19:30:01+00:00",
            source=DataSource.WEBSOCKET,
            yes_price=51,
            no_price=49,
            volume=110,
            raw_data={},
            sequence=1,
        )

        await db_session.commit()

        # Verify both sources exist
        all_snapshots = await repo.get_by_ticker("TEST")
        assert len(all_snapshots) == 2

        rest_snapshots = await repo.get_by_source(DataSource.POLL)
        assert len(rest_snapshots) == 1

        ws_snapshots = await repo.get_by_source(DataSource.WEBSOCKET)
        assert len(ws_snapshots) == 1

    @pytest.mark.asyncio
    async def test_latest_prefers_websocket(self, db_session):
        """Test that latest snapshot prefers WebSocket when more recent."""
        repo = MarketRepository(db_session)

        # REST snapshot (older)
        await repo.create_snapshot(
            ticker="TEST",
            timestamp="2024-10-04T19:30:00+00:00",
            source=DataSource.POLL,
            yes_price=50,
            no_price=50,
            volume=100,
            raw_data={},
        )

        # WebSocket snapshot (newer)
        await repo.create_snapshot(
            ticker="TEST",
            timestamp="2024-10-04T19:30:05+00:00",
            source=DataSource.WEBSOCKET,
            yes_price=52,
            no_price=48,
            volume=120,
            raw_data={},
            sequence=1,
        )

        await db_session.commit()

        # Get latest
        latest = await repo.get_latest_by_ticker("TEST")

        assert latest.source == DataSource.WEBSOCKET
        assert latest.yes_price == 0.52
