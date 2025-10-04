# Backend Architecture Documentation

**Project:** Kalshi Market Analytics
**Phase:** 1 (Local Analytics Workbench)
**Version:** 0.1.0
**Last Updated:** 2025-10-03

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [System Design](#system-design)
4. [Directory Structure](#directory-structure)
5. [Data Models](#data-models)
6. [Component Details](#component-details)
7. [Deployment Architecture](#deployment-architecture)
8. [Phase Evolution](#phase-evolution)
9. [Decision Log](#decision-log)

---

## Overview

### Purpose

The Kalshi Analytics backend is a **phased-evolution architecture** designed to support quantitative trading strategy development. It begins as a local analytics workbench (Phase 1) and evolves into a cloud-deployed, multi-user trading platform (Phases 2-4).

### Core Objectives

- **Data Science First:** Jupyter notebooks drive strategy development
- **Type Safety:** Pydantic v2 throughout for validation and configuration
- **Production Ready:** Clean architecture that scales from prototype to production
- **Cloud Native:** GCP-ready from day 1 with Docker containerization

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Web Framework** | FastAPI 0.104+ | Async REST API with automatic OpenAPI docs |
| **Validation** | Pydantic v2.5+ | Request/response validation, settings management |
| **Database** | PostgreSQL 15+ | Transactional storage for market snapshots |
| **ORM** | SQLAlchemy 2.0 | Async database access with type safety |
| **HTTP Client** | httpx 0.25+ | Async Kalshi API client |
| **Migrations** | Alembic 1.12+ | Database schema version control |
| **Resilience** | tenacity | Retry logic for external API calls |
| **Rate Limiting** | slowapi | API rate limiting for protection |

---

## Architecture Principles

### 1. Separation of Concerns

**Layered Architecture:**
```
api/ → domain/ → infrastructure/
 ↓        ↓            ↓
HTTP   Business    External
Layer    Logic     Systems
```

- **API Layer:** HTTP routing, request validation, dependency injection
- **Domain Layer:** Business logic (implied probabilities, signal evaluation)
- **Infrastructure Layer:** External systems (Kalshi API, database, polling)

**Benefits:**
- Testable business logic (no HTTP/database coupling)
- Easy to swap implementations (e.g., PostgreSQL → TimescaleDB)
- Clear mental model for developers learning FastAPI

### 2. Async-First Design

All I/O operations use `async/await`:

```python
# Database access
async def get_market(ticker: str, db: AsyncSession) -> Market:
    result = await db.execute(select(Market).where(Market.ticker == ticker))
    return result.scalar_one_or_none()

# External API calls
async def fetch_markets(self) -> list[KalshiMarket]:
    response = await self.client.get("/markets")
    return response.json()
```

**Why Async:**
- Non-blocking I/O enables high concurrency
- Supports WebSocket connections (Phase 2)
- Efficient background task management

### 3. Type Safety Everywhere

**Pydantic v2 for all data validation:**

```python
# Configuration
class Settings(BaseSettings):
    KALSHI_API_BASE: str
    DB_URL: str

# API contracts
class MarketResponse(BaseModel):
    ticker: str
    yes_price: Decimal

# External API validation
class KalshiMarket(BaseModel):
    ticker: str
    yes_price: float = Field(alias="yes_bid")
```

**Benefits:**
- Runtime validation catches errors early
- IDE autocomplete and type checking (mypy)
- Self-documenting code

### 4. Repository Pattern

**Decouple business logic from data access:**

```python
# Protocol (interface)
class MarketRepository(Protocol):
    async def get_latest(self, ticker: str) -> MarketSnapshot | None: ...
    async def save(self, snapshot: MarketSnapshot) -> None: ...

# Implementation
class SQLAlchemyMarketRepo:
    def __init__(self, session: AsyncSession):
        self.session = session
```

**Benefits:**
- Services depend on Protocol, not SQLAlchemy
- Easy to mock for testing
- Database implementation can change without affecting business logic

### 5. Container Separation

**Critical for multi-instance deployment:**

```yaml
# docker-compose.yml
services:
  api:      # Scales horizontally (N instances)
  poller:   # Runs as singleton (1 instance)
  postgres: # Shared state
```

**Why This Matters:**
- Phase 3 (GCP) auto-scales API instances
- Polling must run as single coordinated process
- Prevents duplicate API calls and rate limit violations

---

## System Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                   (React + TypeScript)                       │
└─────────────────────────┬───────────────────────────────────┘
                          │ HTTP REST
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                      API Container                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  FastAPI Application                                  │  │
│  │  - Health checks                                      │  │
│  │  - Rate limiting                                      │  │
│  │  - Exception handling                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Routes (/api/v1/markets, /api/v1/backtests)         │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Domain Services                                      │  │
│  │  - Market analytics (implied probability)            │  │
│  │  - Strategy evaluation                                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Repositories (Data Access Layer)                     │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓ PostgreSQL
               ┌───────────────┐
               │   Database    │
               │   - Snapshots │
               │   - Backtests │
               └───────┬───────┘
                       ↑
                       │ Write snapshots
┌──────────────────────┴───────────────────────────────────────┐
│                    Poller Container                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Background Polling Service                           │   │
│  │  - 5-second interval                                  │   │
│  │  - Retry logic with exponential backoff              │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Kalshi API Client                                    │   │
│  │  - httpx async client                                 │   │
│  │  - Connection pooling                                 │   │
│  │  - Timeout strategy                                   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
                       ↓
           ┌───────────────────────┐
           │   Kalshi Demo API     │
           │  (External Service)   │
           └───────────────────────┘
```

### Request Flow

**1. API Request (GET /api/v1/markets?status=active)**

```
User → Frontend → API Container → Repository → Database → Response
                        ↓
                  Rate Limiter (10/min)
                        ↓
                  Validation (Pydantic)
                        ↓
                  Business Logic
```

**2. Background Polling (Every 5 seconds)**

```
Poller Container → Kalshi API → Parse Response → Repository → Database
       ↓                              ↓
  Retry Logic                   Pydantic Validation
  (3 attempts)                  (KalshiMarket schema)
```

---

## Directory Structure

### Complete Layout

```
backend/
├── api/                          # HTTP Layer
│   ├── __init__.py
│   ├── main.py                   # FastAPI app, lifespan, middleware
│   ├── deps.py                   # Dependency injection (DB sessions, etc.)
│   └── v1/                       # API version 1
│       ├── __init__.py
│       ├── markets.py            # Market endpoints
│       ├── backtests.py          # Backtesting endpoints
│       └── health.py             # Health check endpoint
│
├── domain/                       # Business Logic
│   ├── __init__.py
│   ├── market.py                 # Market analytics (implied probability, etc.)
│   └── strategy.py               # Strategy evaluation logic
│
├── infrastructure/               # External Systems
│   ├── __init__.py
│   ├── kalshi/
│   │   ├── __init__.py
│   │   ├── client.py             # Async httpx client with retry logic
│   │   └── schemas.py            # Pydantic models for Kalshi API responses
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py             # SQLAlchemy models
│   │   └── repositories.py       # Repository implementations
│   └── polling/
│       ├── __init__.py
│       └── poller.py             # Standalone polling script
│
├── schemas/                      # API Contracts
│   ├── __init__.py
│   ├── requests.py               # API request models
│   └── responses.py              # API response models
│
├── core/                         # Cross-Cutting Concerns
│   ├── __init__.py
│   ├── config.py                 # Pydantic Settings
│   ├── database.py               # Database connection, session factory
│   └── logging.py                # Structured logging configuration
│
├── alembic/                      # Database Migrations
│   ├── versions/
│   │   └── 001_initial_schema.py
│   └── env.py
│
├── tests/                        # Test Suite
│   ├── __init__.py
│   ├── conftest.py               # Pytest fixtures
│   ├── test_api/
│   │   ├── test_markets.py
│   │   └── test_backtests.py
│   ├── test_domain/
│   │   └── test_market.py
│   └── test_infrastructure/
│       ├── test_kalshi_client.py
│       └── test_repositories.py
│
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies (pytest, mypy, etc.)
├── pyproject.toml                # Project metadata, tool configs
├── alembic.ini                   # Alembic configuration
├── .env.example                  # Environment variable template
├── Dockerfile                    # API container image
├── Dockerfile.poller             # Poller container image
├── docker-compose.yml            # Multi-container orchestration
└── README.md                     # Setup instructions
```

### Design Rationale

| Directory | Purpose | Access Pattern |
|-----------|---------|----------------|
| `api/` | HTTP routing and request handling | Entry point for all API requests |
| `domain/` | Pure business logic (no dependencies on infrastructure) | Called by API routes |
| `infrastructure/` | External system integrations (DB, Kalshi API) | Used by domain and API |
| `schemas/` | API request/response contracts | Used by API routes for validation |
| `core/` | Configuration, database setup, logging | Imported globally |
| `alembic/` | Database schema version control | Run via CLI for migrations |
| `tests/` | Test suite mirroring src structure | Run via pytest |

---

## Data Models

### 1. MarketSnapshot (Database)

**Purpose:** Store timestamped market data for historical analysis and backtesting.

**Schema:**

```python
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from enum import Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, JSON, Numeric, Index, UniqueConstraint

class DataSource(str, Enum):
    POLL = "poll"           # 5-second REST polling (Phase 1)
    WEBSOCKET = "websocket" # Real-time WebSocket (Phase 2)
    BACKFILL = "backfill"   # Historical data import

class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Market Identifiers
    ticker: Mapped[str] = mapped_column(String(50), index=True)

    # Timestamp (timezone-aware for market hours)
    timestamp: Mapped[datetime] = mapped_column(index=True)  # TIMESTAMPTZ in PostgreSQL

    # Data Provenance
    source: Mapped[DataSource] = mapped_column(index=True)
    sequence: Mapped[int | None] = mapped_column()  # WebSocket sequence for gap detection

    # Market Data
    yes_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    no_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    volume: Mapped[int]
    open_interest: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))

    # Full API Response (for future analysis)
    raw_data: Mapped[dict] = mapped_column(JSON)

    # Audit
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    __table_args__ = (
        UniqueConstraint('ticker', 'timestamp', 'source', name='uq_ticker_timestamp_source'),
        Index('idx_ticker_timestamp', 'ticker', 'timestamp'),
    )
```

**Design Notes:**
- `source` enables debugging (poll vs WebSocket data)
- `sequence` allows gap detection in Phase 2 WebSocket streams
- `raw_data` preserves full API response for unforeseen analysis needs
- Unique constraint prevents duplicate snapshots
- Composite index optimizes time-range queries

**Example Query:**
```python
# Get 1-hour price history for backtesting
snapshots = await db.execute(
    select(MarketSnapshot)
    .where(
        MarketSnapshot.ticker == "PREZDEM2024",
        MarketSnapshot.timestamp >= start_time,
        MarketSnapshot.timestamp <= end_time
    )
    .order_by(MarketSnapshot.timestamp)
)
```

---

### 2. BacktestResult (Database)

**Purpose:** Store backtest execution results with full audit trail.

**Schema:**

```python
class BacktestResult(Base):
    __tablename__ = "backtest_results"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Strategy Identification
    strategy_name: Mapped[str] = mapped_column(String(100), index=True)
    strategy_version: Mapped[str] = mapped_column(String(50))  # Git hash or semver

    # Time Range
    start_date: Mapped[date]
    end_date: Mapped[date]

    # Performance Metrics
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    sharpe_ratio: Mapped[Decimal] = mapped_column(Numeric(6, 3))
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    win_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))  # 0.0000 to 1.0000
    num_trades: Mapped[int]

    # Strategy Parameters
    metadata: Mapped[dict] = mapped_column(JSON)  # {"threshold": 0.05, "market_filter": "politics"}

    # Audit
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
```

**Related Model: BacktestExecution (Trade-Level Detail)**

```python
class BacktestExecution(Base):
    __tablename__ = "backtest_executions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Foreign Keys
    backtest_id: Mapped[UUID] = mapped_column(ForeignKey("backtest_results.id"), index=True)
    entry_snapshot_id: Mapped[UUID] = mapped_column(ForeignKey("market_snapshots.id"))
    exit_snapshot_id: Mapped[UUID | None] = mapped_column(ForeignKey("market_snapshots.id"))

    # Trade Details
    entry_time: Mapped[datetime]
    exit_time: Mapped[datetime | None]
    entry_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    position_size: Mapped[int]
    pnl: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    # Signal Metadata (why did strategy enter/exit?)
    signal_metadata: Mapped[dict] = mapped_column(JSON)
```

**Design Notes:**
- `strategy_version` enables comparing v1 vs v2 performance
- `BacktestExecution` provides audit trail for debugging bad trades
- Foreign keys link executions to exact `MarketSnapshot` data (reproducibility)
- `signal_metadata` stores reasoning (e.g., `{"reason": "price_spike", "threshold": 0.05}`)

**Example Query:**
```python
# Compare strategy versions
v1_results = await db.execute(
    select(BacktestResult)
    .where(
        BacktestResult.strategy_name == "fade_overreaction",
        BacktestResult.strategy_version == "v1.0.0"
    )
)

v2_results = await db.execute(
    select(BacktestResult)
    .where(
        BacktestResult.strategy_name == "fade_overreaction",
        BacktestResult.strategy_version == "v2.0.0"
    )
)
```

---

### 3. Pydantic Models (API Validation)

**KalshiMarket (External API Response):**

```python
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

class KalshiMarket(BaseModel):
    """Validates Kalshi API /markets response"""
    ticker: str
    title: str
    category: str
    yes_price: Decimal = Field(alias="yes_bid")  # API uses "yes_bid"
    no_price: Decimal = Field(alias="no_bid")
    volume: int
    open_interest: int
    close_time: datetime
    status: Literal["active", "closed", "settled"]

    model_config = {
        "populate_by_name": True  # Accept both "yes_price" and "yes_bid"
    }
```

**MarketResponse (API Output):**

```python
class MarketResponse(BaseModel):
    """Public API response for market data"""
    ticker: str
    title: str
    yes_price: Decimal
    no_price: Decimal
    implied_probability: Decimal  # Calculated: yes_price / 100
    volume: int
    status: str
    last_updated: datetime
```

**BacktestRequest (API Input):**

```python
class BacktestRequest(BaseModel):
    """Request body for POST /api/v1/backtests"""
    strategy: str = Field(..., min_length=1, max_length=100)
    market_filter: str | None = Field(None, description="e.g., 'politics', 'sports'")
    start_date: date
    end_date: date

    @field_validator('end_date')
    def end_after_start(cls, v, info):
        if 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
```

---

## Component Details

### 1. FastAPI Application (api/main.py)

**Responsibilities:**
- Application initialization and lifespan management
- Middleware configuration (CORS, rate limiting, logging)
- Route registration
- Global exception handling

**Key Code:**

```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.v1 import markets, backtests, health
from core.config import settings
from core.database import engine, Base
from core.logging import setup_logging

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle"""
    # Startup
    setup_logging(settings.LOG_LEVEL)
    logger.info("Starting Kalshi Analytics API")

    # Create database tables (production uses Alembic migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Shutdown
    logger.info("Shutting down Kalshi Analytics API")
    await engine.dispose()

app = FastAPI(
    title="Kalshi Analytics API",
    version="0.1.0",
    description="REST API for Kalshi market analysis and backtesting",
    lifespan=lifespan
)

# Middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "path": str(request.url),
            "method": request.method
        }
    )

# Route registration
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(markets.router, prefix="/api/v1", tags=["markets"])
app.include_router(backtests.router, prefix="/api/v1", tags=["backtests"])
```

**Design Notes:**
- Lifespan context manager handles startup/shutdown cleanly
- Rate limiting protects against abuse (10 requests/minute default)
- CORS configured for frontend at `http://localhost:5173`
- Versioned routes (`/api/v1/`) enable future API evolution

---

### 2. Kalshi API Client (infrastructure/kalshi/client.py)

**Responsibilities:**
- Async HTTP client for Kalshi demo API
- Retry logic with exponential backoff
- Connection pooling and timeout management
- Response validation with Pydantic

**Key Code:**

```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from infrastructure.kalshi.schemas import KalshiMarket, KalshiOrderBook
from core.logging import logger

class KalshiClient:
    """Async client for Kalshi API with resilience patterns"""

    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout, connect=5.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def get_markets(
        self,
        status: str | None = None,
        limit: int = 100
    ) -> list[KalshiMarket]:
        """
        Fetch markets with optional status filter.

        Args:
            status: Filter by market status ("active", "closed", "settled")
            limit: Maximum markets to return (default 100)

        Returns:
            List of validated KalshiMarket objects

        Raises:
            httpx.HTTPError: On API request failure (after retries)
        """
        params = {"limit": limit}
        if status:
            params["status"] = status

        logger.debug(f"Fetching markets: {params}")
        response = await self.client.get(f"{self.base_url}/markets", params=params)
        response.raise_for_status()

        data = response.json()
        return [KalshiMarket(**market) for market in data.get("markets", [])]

    async def get_market(self, ticker: str) -> KalshiMarket:
        """Get single market by ticker"""
        response = await self.client.get(f"{self.base_url}/markets/{ticker}")
        response.raise_for_status()
        return KalshiMarket(**response.json())

    async def close(self):
        """Close HTTP client connection pool"""
        await self.client.aclose()
```

**Resilience Features:**
- **Retry Logic:** 3 attempts with exponential backoff (2s, 4s, 8s)
- **Timeouts:** 10s total, 5s connect (prevents hanging)
- **Connection Pooling:** Max 10 concurrent connections
- **Validation:** Pydantic ensures API contract compliance

---

### 3. Market Poller (infrastructure/polling/poller.py)

**Responsibilities:**
- Poll Kalshi API every 5 seconds
- Store market snapshots in database
- Handle errors with retry and backoff
- Run as standalone container (singleton)

**Key Code:**

```python
import asyncio
from datetime import datetime, UTC
from infrastructure.kalshi.client import KalshiClient
from infrastructure.database.repositories import MarketSnapshotRepository
from infrastructure.database.models import DataSource
from core.config import settings
from core.database import AsyncSessionLocal
from core.logging import logger

async def run_poller():
    """
    Main polling loop - runs as standalone container.

    This is a SEPARATE container from the API to prevent:
    - Duplicate polling when API scales to multiple instances
    - Rate limit violations from multiple pollers
    """
    kalshi_client = KalshiClient(settings.KALSHI_API_BASE)

    logger.info(f"Starting poller (interval={settings.POLL_INTERVAL_SECONDS}s)")

    while True:
        try:
            async with AsyncSessionLocal() as session:
                repo = MarketSnapshotRepository(session)

                # Fetch active markets from Kalshi
                markets = await kalshi_client.get_markets(status="active")
                logger.info(f"Fetched {len(markets)} active markets")

                # Store snapshots
                timestamp = datetime.now(UTC)
                for market in markets:
                    await repo.save_snapshot(
                        ticker=market.ticker,
                        timestamp=timestamp,
                        source=DataSource.POLL,
                        yes_price=market.yes_price,
                        no_price=market.no_price,
                        volume=market.volume,
                        open_interest=market.open_interest,
                        status=market.status,
                        raw_data=market.model_dump()
                    )

                await session.commit()
                logger.debug(f"Stored {len(markets)} snapshots")

        except Exception as e:
            logger.error(f"Polling error: {e}", exc_info=True)

        await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    asyncio.run(run_poller())
```

**Critical Design Decision:**
This runs as a **separate Docker container**, not in FastAPI lifespan. Why?

**Problem (if in lifespan):**
```yaml
# GCP Cloud Run scales API to 3 instances
api-instance-1: poller runs → polls Kalshi every 5s
api-instance-2: poller runs → polls Kalshi every 5s  # DUPLICATE
api-instance-3: poller runs → polls Kalshi every 5s  # DUPLICATE
# Result: 3x API calls, rate limit violations, duplicate data
```

**Solution (separate container):**
```yaml
poller: 1 instance → polls Kalshi every 5s
api: N instances → handle HTTP requests
# Result: Clean separation, scales independently
```

---

### 4. Repository Pattern (infrastructure/database/repositories.py)

**Responsibilities:**
- Abstract data access logic from business code
- Provide clean interface for database operations
- Enable testing with mock repositories

**Key Code:**

```python
from typing import Protocol
from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from infrastructure.database.models import MarketSnapshot, DataSource

class MarketSnapshotRepository(Protocol):
    """Repository interface (protocol)"""

    async def get_latest(self, ticker: str) -> MarketSnapshot | None:
        """Get most recent snapshot for ticker"""
        ...

    async def get_range(
        self,
        ticker: str,
        start: datetime,
        end: datetime
    ) -> list[MarketSnapshot]:
        """Get snapshots within time range"""
        ...

    async def save_snapshot(
        self,
        ticker: str,
        timestamp: datetime,
        source: DataSource,
        **kwargs
    ) -> MarketSnapshot:
        """Create and save new snapshot"""
        ...

class SQLAlchemyMarketRepo:
    """SQLAlchemy implementation of MarketSnapshotRepository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_latest(self, ticker: str) -> MarketSnapshot | None:
        result = await self.session.execute(
            select(MarketSnapshot)
            .where(MarketSnapshot.ticker == ticker)
            .order_by(MarketSnapshot.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_range(
        self,
        ticker: str,
        start: datetime,
        end: datetime
    ) -> list[MarketSnapshot]:
        result = await self.session.execute(
            select(MarketSnapshot)
            .where(
                MarketSnapshot.ticker == ticker,
                MarketSnapshot.timestamp >= start,
                MarketSnapshot.timestamp <= end
            )
            .order_by(MarketSnapshot.timestamp)
        )
        return list(result.scalars().all())

    async def save_snapshot(
        self,
        ticker: str,
        timestamp: datetime,
        source: DataSource,
        **kwargs
    ) -> MarketSnapshot:
        snapshot = MarketSnapshot(
            ticker=ticker,
            timestamp=timestamp,
            source=source,
            **kwargs
        )
        self.session.add(snapshot)
        return snapshot
```

**Benefits:**
- Business logic depends on `Protocol`, not SQLAlchemy
- Easy to swap PostgreSQL → TimescaleDB in Phase 3
- Testable with in-memory mock implementation

---

## Deployment Architecture

### Phase 1: Local Development

**Docker Compose Setup:**

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: kalshi
      POSTGRES_USER: kalshi_user
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  poller:
    build:
      context: ./backend
      dockerfile: Dockerfile.poller
    environment:
      KALSHI_API_BASE: https://demo-api.kalshi.com/v2
      DB_URL: postgresql+asyncpg://kalshi_user:dev_password@postgres/kalshi  # pragma: allowlist secret
      POLL_INTERVAL_SECONDS: 5
      LOG_LEVEL: INFO
    depends_on:
      - postgres
    restart: unless-stopped

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      KALSHI_API_BASE: https://demo-api.kalshi.com/v2
      DB_URL: postgresql+asyncpg://kalshi_user:dev_password@postgres/kalshi  # pragma: allowlist secret
      LOG_LEVEL: DEBUG
      CORS_ORIGINS: '["http://localhost:5173"]'
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - poller
    volumes:
      - ./backend:/app  # Hot reload for development

volumes:
  postgres_data:
```

**Key Points:**
- **postgres:** Shared database for both API and poller
- **poller:** Singleton container, runs polling script
- **api:** Can scale horizontally (add `--scale api=3`)
- **volumes:** Mount backend for hot reload during development

---

### Phase 3: GCP Cloud Deployment

**Architecture:**

```
Internet
    ↓
Cloud Load Balancer
    ↓
Cloud Run (api) ← Auto-scales 0-10 instances
    ↓
Cloud SQL (PostgreSQL) ← Managed database
    ↑
Cloud Run (poller) ← Always 1 instance
```

**GCP Services:**

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **Cloud Run (API)** | API container | Min: 0, Max: 10 instances, auto-scale on CPU/requests |
| **Cloud Run (Poller)** | Polling container | Min: 1, Max: 1 instance, singleton enforced |
| **Cloud SQL** | PostgreSQL 15 | HA with read replicas (Phase 4) |
| **Secret Manager** | API keys, DB credentials | Injected as env vars |
| **Cloud Logging** | Centralized logs | Structured JSON logs |
| **Cloud Monitoring** | Metrics and alerts | Latency, error rate, uptime |

**Deployment Commands:**

```bash
# Build and push containers
gcloud builds submit --tag gcr.io/PROJECT_ID/kalshi-api:v1
gcloud builds submit --tag gcr.io/PROJECT_ID/kalshi-poller:v1

# Deploy API (auto-scaling)
gcloud run deploy kalshi-api \
  --image gcr.io/PROJECT_ID/kalshi-api:v1 \
  --min-instances 0 \
  --max-instances 10 \
  --set-env-vars DB_URL=secret://db-url

# Deploy Poller (singleton)
gcloud run deploy kalshi-poller \
  --image gcr.io/PROJECT_ID/kalshi-poller:v1 \
  --min-instances 1 \
  --max-instances 1 \
  --set-env-vars DB_URL=secret://db-url
```

---

## Phase Evolution

### Phase 1 → Phase 2 (Add WebSocket)

**Changes Required:**

1. **New Container:** WebSocket consumer service
2. **Data Model:** Already supports `source=websocket`, `sequence` field
3. **Database:** Add index on `sequence` for gap detection
4. **Frontend:** Add WebSocket client for real-time updates

**Architecture:**

```
Kalshi WebSocket API
         ↓
WebSocket Consumer (new container)
         ↓
PostgreSQL (append-only snapshots)
         ↓
API Container (reads latest snapshots)
         ↓
Frontend (WebSocket updates)
```

**No Breaking Changes:**
- Poller continues running (fallback for WebSocket downtime)
- API routes unchanged
- Database schema already prepared

---

### Phase 2 → Phase 3 (Add Automation)

**Changes Required:**

1. **New Service:** Trade executor (Cloud Tasks or Celery)
2. **Database:** Add `Trade` model for execution history
3. **API:** Add `/api/v1/trades` endpoints
4. **Monitoring:** Add alerts for trade failures

**Architecture:**

```
Strategy Notebook → Generates trade signals
         ↓
API POST /api/v1/trades → Validates signal
         ↓
Cloud Tasks Queue → Asynchronous execution
         ↓
Trade Executor → Calls Kalshi trading API
         ↓
Database (audit trail)
```

---

### Phase 3 → Phase 4 (Add GraphQL + Multi-User)

**Changes Required:**

1. **GraphQL Layer:** Add Strawberry GraphQL on top of REST
2. **Authentication:** Firebase Auth or Auth0
3. **Caching:** Redis for session and query caching
4. **Database:** Add `User` and `Subscription` models

**Architecture:**

```
Frontend → GraphQL Client (Apollo)
         ↓
API Container → Strawberry resolvers
         ↓
Redis (DataLoader caching)
         ↓
PostgreSQL (data)
```

**Backward Compatibility:**
- REST API remains available (`/api/v1/`)
- GraphQL is overlay, not replacement
- Existing API clients unaffected

---

## Decision Log

### ADR-001: Separate Poller Container

**Date:** 2025-10-03
**Status:** Accepted

**Context:**
Background polling can be implemented in FastAPI lifespan or as separate container.

**Decision:**
Extract poller as standalone Docker container from day 1.

**Rationale:**
- **Multi-instance safety:** GCP auto-scaling won't create duplicate pollers
- **Independent scaling:** API scales on traffic, poller runs at constant rate
- **Failure isolation:** Poller crash doesn't affect API
- **Deployment flexibility:** Can deploy poller updates independently

**Consequences:**
- **Positive:** Clean architecture for Phases 3-4, prevents future refactor
- **Negative:** Slight complexity increase (2 containers vs 1)
- **Mitigation:** Docker Compose makes local development simple

---

### ADR-002: Repository Pattern

**Date:** 2025-10-03
**Status:** Accepted

**Context:**
Services can use SQLAlchemy directly or go through repository abstraction.

**Decision:**
Implement repository pattern with Protocol interfaces.

**Rationale:**
- **Testability:** Easy to mock for unit tests
- **Flexibility:** Can swap PostgreSQL → TimescaleDB without changing business logic
- **Separation:** Domain logic doesn't depend on infrastructure details

**Consequences:**
- **Positive:** Clean architecture, testable, future-proof
- **Negative:** Extra abstraction layer (more files)
- **Mitigation:** Protocol keeps interface simple

---

### ADR-003: Phase 2 Data Model Preparation

**Date:** 2025-10-03
**Status:** Accepted

**Context:**
Phase 1 only needs polling, but Phase 2 will add WebSocket.

**Decision:**
Add `source`, `sequence`, and timezone-aware timestamps in Phase 1.

**Rationale:**
- **Forward compatibility:** No schema migration needed for Phase 2
- **Debugging:** `source` field helps identify data issues
- **Minimal cost:** Extra columns have negligible storage impact

**Consequences:**
- **Positive:** Smooth Phase 2 transition, better debugging
- **Negative:** Slight complexity in Phase 1 (unused fields)
- **Mitigation:** Fields are optional, don't complicate logic

---

### ADR-004: PostgreSQL First (No Redis in Phase 1)

**Date:** 2025-10-03
**Status:** Accepted

**Context:**
Could use Redis for caching market snapshots.

**Decision:**
Use PostgreSQL only for Phase 1, defer Redis to Phase 3+.

**Rationale:**
- **Simplicity:** One database to manage
- **Sufficient performance:** Single-user local tool doesn't need caching
- **YAGNI:** Premature optimization

**Consequences:**
- **Positive:** Simpler deployment, fewer moving parts
- **Negative:** May need caching for multi-user Phase 3
- **Mitigation:** Architecture supports adding Redis layer without code changes

---

## Appendix

### Environment Variables

**.env.example:**

```bash
# Kalshi API
KALSHI_API_BASE=https://demo-api.kalshi.com/v2
POLL_INTERVAL_SECONDS=5

# Database
DB_URL=postgresql+asyncpg://user:password@localhost:5432/kalshi  # pragma: allowlist secret

# Application
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:5173"]

# Phase 2+ (WebSocket)
# KALSHI_WS_URL=wss://demo-api.kalshi.com/trade-api/ws

# Phase 3+ (GCP)
# GCP_PROJECT_ID=kalshi-analytics
# REDIS_URL=redis://localhost:6379
```

### Common Commands

```bash
# Development
docker-compose up --build        # Start all services
docker-compose logs -f poller    # Watch poller logs
docker-compose exec api bash     # Shell into API container

# Database
docker-compose exec postgres psql -U kalshi_user -d kalshi
alembic upgrade head             # Run migrations
alembic revision --autogenerate -m "description"  # Create migration

# Testing
pytest tests/ -v                 # Run all tests
pytest tests/test_api/ -v        # API tests only
mypy backend/                    # Type checking

# Production
gcloud run deploy kalshi-api --image gcr.io/PROJECT/kalshi-api:v1
gcloud run deploy kalshi-poller --image gcr.io/PROJECT/kalshi-poller:v1
```

### Performance Benchmarks (Target)

| Metric | Phase 1 | Phase 3 (Multi-User) |
|--------|---------|---------------------|
| **API Latency** | <100ms p95 | <200ms p95 |
| **Polling Reliability** | >99% uptime | >99.9% uptime |
| **Database Query** | <50ms p95 | <100ms p95 |
| **Backtest Execution** | <10s for 1000 snapshots | <30s for 10000 snapshots |

---

**Document Version:** 1.0
**Author:** System Architect Agent
**Review Date:** 2025-10-03
