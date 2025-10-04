"""Integration tests for Markets API endpoints."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient

from domain.models import MarketSnapshot
from domain.models.market import DataSource
from domain.repositories import MarketRepository


class TestMarketsAPI:
    """Integration tests for /api/v1/markets endpoints."""

    async def test_get_all_markets_empty(self, client: AsyncClient) -> None:
        """Test getting all markets when database is empty."""
        response = await client.get("/api/v1/markets")

        assert response.status_code == 200
        data = response.json()
        assert data["snapshots"] == []
        assert data["total"] == 0

    async def test_get_all_markets(
        self, client: AsyncClient, market_repository: MarketRepository
    ) -> None:
        """Test getting all latest market snapshots."""
        # Create snapshots for multiple tickers
        now = datetime.now(UTC)
        for i in range(3):
            await market_repository.create_snapshot(
                ticker=f"TICKER-{i:03d}",
                timestamp=now,
                source=DataSource.POLL,
                yes_price=50.0 + i,
                no_price=50.0 - i,
                volume=1000,
                raw_data={},
            )

        response = await client.get("/api/v1/markets")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["snapshots"]) == 3

    async def test_get_all_markets_pagination(
        self, client: AsyncClient, market_repository: MarketRepository
    ) -> None:
        """Test pagination for all markets."""
        now = datetime.now(UTC)
        for i in range(5):
            await market_repository.create_snapshot(
                ticker=f"TICKER-{i:03d}",
                timestamp=now,
                source=DataSource.POLL,
                yes_price=50.0,
                no_price=50.0,
                volume=1000,
                raw_data={},
            )

        # Get first page
        response = await client.get("/api/v1/markets?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["snapshots"]) == 2
        assert data["skip"] == 0
        assert data["limit"] == 2

        # Get second page
        response = await client.get("/api/v1/markets?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["snapshots"]) == 2

    async def test_get_snapshots_by_ticker(
        self, client: AsyncClient, market_repository: MarketRepository
    ) -> None:
        """Test getting all snapshots for specific ticker."""
        ticker = "TEST-TICKER"
        now = datetime.now(UTC)

        # Create multiple snapshots for same ticker
        for i in range(3):
            await market_repository.create_snapshot(
                ticker=ticker,
                timestamp=now,
                source=DataSource.POLL,
                yes_price=50.0 + i,
                no_price=50.0 - i,
                volume=1000,
                raw_data={},
            )

        response = await client.get(f"/api/v1/markets/{ticker}/snapshots")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert all(s["ticker"] == ticker for s in data["snapshots"])

    async def test_get_snapshots_by_ticker_empty(self, client: AsyncClient) -> None:
        """Test getting snapshots for non-existent ticker."""
        response = await client.get("/api/v1/markets/NONEXISTENT/snapshots")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["snapshots"] == []

    async def test_get_latest_snapshot(
        self, client: AsyncClient, market_repository: MarketRepository
    ) -> None:
        """Test getting latest snapshot for ticker."""
        ticker = "LATEST-TICKER"
        now = datetime.now(UTC)

        # Create older snapshot
        await market_repository.create_snapshot(
            ticker=ticker,
            timestamp=now,
            source=DataSource.POLL,
            yes_price=45.0,
            no_price=55.0,
            volume=1000,
            raw_data={},
        )

        # Create newer snapshot
        await market_repository.create_snapshot(
            ticker=ticker,
            timestamp=now,
            source=DataSource.POLL,
            yes_price=60.0,
            no_price=40.0,
            volume=2000,
            raw_data={},
        )

        response = await client.get(f"/api/v1/markets/{ticker}/latest")

        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == ticker
        assert Decimal(data["yes_price"]) == Decimal("60.0")
        assert data["volume"] == 2000

    async def test_get_latest_snapshot_not_found(self, client: AsyncClient) -> None:
        """Test getting latest snapshot for non-existent ticker."""
        response = await client.get("/api/v1/markets/NONEXISTENT/latest")

        assert response.status_code == 404
        data = response.json()
        assert "No snapshots found" in data["detail"]

    async def test_get_snapshot_by_id(
        self, client: AsyncClient, sample_market_snapshot: MarketSnapshot
    ) -> None:
        """Test getting snapshot by ID."""
        response = await client.get(f"/api/v1/markets/{sample_market_snapshot.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_market_snapshot.id)
        assert data["ticker"] == sample_market_snapshot.ticker

    async def test_get_snapshot_by_id_not_found(self, client: AsyncClient) -> None:
        """Test getting snapshot by non-existent ID."""
        non_existent_id = uuid4()
        response = await client.get(f"/api/v1/markets/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]

    async def test_get_snapshot_by_id_invalid_uuid(self, client: AsyncClient) -> None:
        """Test getting snapshot with invalid UUID format."""
        response = await client.get("/api/v1/markets/not-a-uuid")

        assert response.status_code == 422  # Unprocessable Entity

    async def test_pagination_validation(self, client: AsyncClient) -> None:
        """Test pagination parameter validation."""
        # Negative skip
        response = await client.get("/api/v1/markets?skip=-1")
        assert response.status_code == 422

        # Limit too high
        response = await client.get("/api/v1/markets?limit=10000")
        assert response.status_code == 422

        # Limit too low
        response = await client.get("/api/v1/markets?limit=0")
        assert response.status_code == 422

    async def test_response_schema_validation(
        self, client: AsyncClient, market_repository: MarketRepository
    ) -> None:
        """Test that response matches expected schema."""
        await market_repository.create_snapshot(
            ticker="SCHEMA-TEST",
            timestamp=datetime.now(UTC),
            source=DataSource.POLL,
            yes_price=55.5,
            no_price=44.5,
            volume=10000,
            raw_data={"test": "data"},
        )

        response = await client.get("/api/v1/markets/SCHEMA-TEST/latest")

        assert response.status_code == 200
        data = response.json()

        # Verify all expected fields are present
        required_fields = [
            "id",
            "ticker",
            "timestamp",
            "source",
            "yes_price",
            "no_price",
            "volume",
            "created_at",
        ]
        for field in required_fields:
            assert field in data, f"Field '{field}' not found in response"

        # Verify data types
        assert isinstance(data["id"], str)
        assert isinstance(data["ticker"], str)
        assert isinstance(data["volume"], int)
        assert isinstance(data["source"], str)
