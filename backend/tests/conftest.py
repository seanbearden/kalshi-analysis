"""Shared test fixtures and configuration."""

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from domain.models import BacktestResult, MarketSnapshot
from domain.models.backtest import StrategyType
from domain.models.market import DataSource
from domain.repositories import BacktestRepository, MarketRepository
from infrastructure.database.base import Base
from infrastructure.database.session import get_session

# Set minimal environment variables for test imports
# Note: We use PostgreSQL URL format to satisfy Pydantic validation,
# but tests use in-memory SQLite with overridden fixtures
os.environ.setdefault(
    "DB_URL",
    "postgresql+asyncpg://test:test@localhost:5432/test",  # pragma: allowlist secret
)
os.environ.setdefault("KALSHI_API_BASE", "https://demo-api.kalshi.co/trade-api/v2")

from main import app  # noqa: E402


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Provide test database URL (SQLite in-memory)."""
    return "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
async def test_engine(test_db_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine."""
    engine = create_async_engine(test_db_url, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    session_maker = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_maker() as session:
        yield session
        await session.rollback()  # Rollback after each test


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create FastAPI test client with overridden dependencies."""

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = override_get_session

    from httpx import ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def market_repository(session: AsyncSession) -> MarketRepository:
    """Create MarketRepository instance."""
    return MarketRepository(session)


@pytest.fixture
async def backtest_repository(session: AsyncSession) -> BacktestRepository:
    """Create BacktestRepository instance."""
    return BacktestRepository(session)


@pytest.fixture
async def sample_market_snapshot(session: AsyncSession) -> MarketSnapshot:
    """Create and persist a sample market snapshot."""
    snapshot = MarketSnapshot(
        ticker="PRES-2024",
        timestamp=datetime.now(UTC),
        source=DataSource.POLL,
        yes_price=Decimal("55.50"),
        no_price=Decimal("44.50"),
        volume=10000,
        raw_data={"event_ticker": "PRES", "market_ticker": "PRES-2024"},
    )
    session.add(snapshot)
    await session.commit()
    await session.refresh(snapshot)
    return snapshot


@pytest.fixture
async def sample_backtest_result(session: AsyncSession) -> BacktestResult:
    """Create and persist a sample backtest result."""
    result = BacktestResult(
        strategy_name="momentum",
        strategy_type=StrategyType.MOMENTUM,
        strategy_version="v1.0.0",
        start_date=datetime(2024, 1, 1).date(),
        end_date=datetime(2024, 3, 31).date(),
        total_pnl=Decimal("1250.00"),
        sharpe_ratio=Decimal("1.45"),
        max_drawdown=Decimal("-350.00"),
        win_rate=Decimal("0.6500"),
        num_trades=20,
        metadata={"threshold": 0.05, "market_filter": "politics"},
    )
    session.add(result)
    await session.commit()
    await session.refresh(result)
    return result


@pytest.fixture
def mock_kalshi_market_response() -> dict[str, Any]:
    """Sample Kalshi API market response."""
    return {
        "ticker": "PRES-2024",
        "title": "Will Biden win the 2024 presidential election?",
        "category": "politics",
        "yes_bid": 55.50,
        "no_bid": 44.50,
        "volume": 10000,
        "open_interest": 5000,
        "close_time": "2024-11-05T23:59:59Z",
        "status": "active",
    }


@pytest.fixture
def mock_kalshi_markets_list() -> list[dict[str, Any]]:
    """Sample Kalshi API markets list response."""
    return [
        {
            "ticker": "PRES-2024",
            "title": "Presidential Election 2024",
            "category": "politics",
            "yes_bid": 55.50,
            "no_bid": 44.50,
            "volume": 10000,
            "open_interest": 5000,
            "status": "active",
        },
        {
            "ticker": "NFL-CHIEFS-SB",
            "title": "Chiefs to win Super Bowl",
            "category": "sports",
            "yes_bid": 30.00,
            "no_bid": 70.00,
            "volume": 5000,
            "open_interest": 2500,
            "status": "active",
        },
    ]
