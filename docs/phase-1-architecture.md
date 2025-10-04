# Phase 1 Architecture: Local Analytics Workbench

**Status**: Active
**Timeline**: 2 weeks
**Goal**: Validate strategy viability through backtesting
**Success Criteria**: Backtest ≥1 strategy with Sharpe ratio >0.5

---

## Architecture Overview

Phase 1 is a **REST-only, polling-based** local analytics platform for Kalshi market data collection and strategy backtesting. This phase focuses on **offline historical analysis**, not live trading.

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│                    Kalshi API (External)                    │
│                 https://demo-api.kalshi.com                 │
└────────────────────────────┬────────────────────────────────┘
                             │ REST (5s polling)
┌────────────────────────────▼────────────────────────────────┐
│              Kalshi Analysis Platform (Local)               │
│                                                             │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │    Poller     │  │   FastAPI    │  │  React Frontend │ │
│  │  Container    │  │   Backend    │  │   (Vite + TS)   │ │
│  │               │  │              │  │                 │ │
│  │ • REST poll   │  │ • REST API   │  │ • Market view   │ │
│  │   every 5s    │  │ • Pydantic   │  │ • Tanstack      │ │
│  │ • Stores to   │  │ • Repository │  │   Query         │ │
│  │   PostgreSQL  │  │   pattern    │  │ • shadcn/ui     │ │
│  └───────┬───────┘  └──────┬───────┘  └─────────────────┘ │
│          │                 │                               │
│          └────────┬────────┘                               │
│                   ▼                                         │
│          ┌─────────────────┐                               │
│          │   PostgreSQL    │                               │
│          │                 │                               │
│          │ • Market        │                               │
│          │   snapshots     │                               │
│          │ • Backtest      │                               │
│          │   results       │                               │
│          └─────────────────┘                               │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Jupyter Notebooks (Local)                    │  │
│  │  • Strategy development  • Backtesting  • Analysis  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Container Architecture

### Three-Container Design (Docker Compose)

```yaml
services:
  # 1. Database
  db:
    image: postgres:15-alpine
    # Stores market snapshots and backtest results

  # 2. Poller (Separate from API - ADR-001)
  poller:
    build: ./backend
    command: python -m poller.main
    # Polls Kalshi API every 5s, writes to PostgreSQL

  # 3. API
  api:
    build: ./backend
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000
    # Serves REST endpoints for frontend
```

**Why Separate Poller?** (ADR-001)
- ✅ GCP Cloud Run auto-scaling won't duplicate polling in Phase 3
- ✅ Independent failure isolation (poller crash ≠ API downtime)
- ✅ Different scaling profiles (API scales on traffic, poller is singleton)
- ✅ 1 hour setup now vs. 2 weeks refactoring later

---

## Backend Architecture

### Directory Structure

```
backend/
├── api/
│   ├── main.py              # FastAPI app, CORS, exception handlers
│   ├── deps.py              # Dependency injection (DB sessions, repos)
│   └── v1/
│       ├── markets.py       # GET /api/v1/markets, /api/v1/markets/{ticker}
│       ├── events.py        # GET /api/v1/events
│       ├── series.py        # GET /api/v1/series/{ticker}
│       └── health.py        # GET /health (GCP health check ready)
│
├── poller/
│   ├── main.py              # Separate container entrypoint (ADR-001)
│   └── kalshi_client.py     # REST API client with retry logic
│
├── repositories/
│   ├── protocols.py         # Protocol interfaces (ADR-002)
│   │   └── MarketRepository(Protocol)
│   └── postgres.py          # PostgreSQL implementations
│       └── PostgresMarketRepository
│
├── models/
│   ├── domain.py            # Pydantic domain models (ADR-003)
│   │   └── MarketSnapshot (source, sequence, timestamp)
│   └── database.py          # SQLAlchemy ORM models
│
├── core/
│   ├── config.py            # Pydantic Settings (env vars)
│   ├── database.py          # SQLAlchemy engine, session factory
│   └── logging.py           # Structured JSON logging
│
└── alembic/                 # Database migrations
    └── versions/
```

### API Endpoints (Phase 1)

```python
# GET /api/v1/markets
# Returns: List of latest market snapshots (one per ticker)
[
  {
    "market_ticker": "INXD-24DEC31-B4500",
    "yes_price": 0.52,
    "no_price": 0.48,
    "volume": 15000,
    "source": "rest",
    "timestamp": "2024-10-04T15:30:00Z"
  }
]

# GET /api/v1/markets/{ticker}/history?limit=100
# Returns: Historical snapshots for backtesting
[
  {
    "market_ticker": "INXD-24DEC31-B4500",
    "yes_price": 0.50,
    "timestamp": "2024-10-04T15:25:00Z",
    ...
  },
  ...
]
```

---

## Critical Architecture Decisions (ADRs)

### ADR-001: Separate Poller Container ⭐

**Decision**: Extract poller as separate Docker container from day 1

**Problem**: Background polling can be implemented in FastAPI lifespan or as separate service

**Anti-Pattern** (DO NOT USE):
```python
# WRONG: Poller in FastAPI lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    poller = MarketPoller()  # Runs in EVERY uvicorn worker
    await poller.start()     # Multiple instances = duplicate polling
```

**Why This Breaks Phase 3**:
- GCP Cloud Run auto-scales to N instances → N pollers → rate limit violations
- No coordination between instances → duplicate database writes
- Requires complete architectural refactor to fix

**Solution**:
```yaml
# docker-compose.yml
services:
  poller:
    build: ./backend
    command: python -m poller.main
    deploy:
      replicas: 1  # ALWAYS exactly 1 instance

  api:
    build: ./backend
    command: uvicorn api.main:app
    deploy:
      replicas: 3  # Can scale horizontally
```

**Implementation**:
```python
# poller/main.py
import asyncio
from kalshi_client import KalshiClient
from repositories.protocols import MarketRepository

async def poll_markets(repo: MarketRepository):
    client = KalshiClient(api_key=settings.KALSHI_API_KEY)

    while True:
        markets = await client.get_markets(status='active')

        for market in markets:
            snapshot = MarketSnapshot(
                market_ticker=market['ticker'],
                yes_price=Decimal(market['yes_price']) / 100,
                no_price=Decimal(market['no_price']) / 100,
                volume=market['volume'],
                source='rest',       # ADR-003: Phase 2-ready
                sequence=None,       # ADR-003: Phase 2-ready
                timestamp=datetime.now(UTC)
            )
            await repo.save(snapshot)

        await asyncio.sleep(5)

if __name__ == '__main__':
    asyncio.run(poll_markets(get_market_repo()))
```

**Benefits**:
- ✅ Phase 3 GCP deployment: API auto-scales, poller stays singleton
- ✅ Failure isolation: poller crash doesn't affect API
- ✅ Independent deployment: update poller without API restart

**Cost**: 1 hour setup now vs. 2 weeks refactoring in Phase 3

---

### ADR-002: Repository Pattern ⭐

**Decision**: Implement repository pattern with Protocol interfaces for data access

**Problem**: How to structure data access layer for testability and flexibility?

**Solution**:
```python
# repositories/protocols.py
from typing import Protocol
from models.domain import MarketSnapshot

class MarketRepository(Protocol):
    """Interface for market data access"""

    async def get_latest(self, ticker: str) -> MarketSnapshot | None:
        """Get latest snapshot for a specific market"""
        ...

    async def get_all_latest(self) -> list[MarketSnapshot]:
        """Get latest snapshot for all markets (one per ticker)"""
        ...

    async def get_history(
        self,
        ticker: str,
        limit: int = 100
    ) -> list[MarketSnapshot]:
        """Get historical snapshots for backtesting"""
        ...

    async def save(self, snapshot: MarketSnapshot) -> None:
        """Store market snapshot"""
        ...
```

```python
# repositories/postgres.py
from sqlalchemy.ext.asyncio import AsyncSession
from repositories.protocols import MarketRepository

class PostgresMarketRepository:
    """PostgreSQL implementation of MarketRepository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_latest(self) -> list[MarketSnapshot]:
        """Fetch latest snapshot per ticker using DISTINCT ON"""
        stmt = (
            select(MarketSnapshotModel)
            .distinct(MarketSnapshotModel.market_ticker)
            .order_by(
                MarketSnapshotModel.market_ticker,
                MarketSnapshotModel.timestamp.desc()
            )
        )
        result = await self.session.execute(stmt)
        return [MarketSnapshot.from_orm(row) for row in result.scalars()]
```

**Dependency Injection**:
```python
# api/deps.py
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import async_session

async def get_db_session() -> AsyncSession:
    async with async_session() as session:
        yield session

def get_market_repo(session: AsyncSession = Depends(get_db_session)):
    return PostgresMarketRepository(session)
```

**Usage in API**:
```python
# api/v1/markets.py
from fastapi import APIRouter, Depends
from repositories.protocols import MarketRepository

router = APIRouter(prefix='/markets', tags=['markets'])

@router.get('/')
async def get_markets(repo: MarketRepository = Depends(get_market_repo)):
    """Get latest snapshot for all markets"""
    snapshots = await repo.get_all_latest()
    return [MarketResponse.from_orm(s) for s in snapshots]
```

**Benefits**:
- ✅ **Testability**: Easy to mock repositories in unit tests
- ✅ **Flexibility**: Swap PostgreSQL → TimescaleDB without changing API
- ✅ **Separation**: Business logic doesn't depend on infrastructure
- ✅ **Phase 2 Ready**: Add WebSocket data source without API changes

**Testing Example**:
```python
# tests/test_markets_api.py
class MockMarketRepo:
    async def get_all_latest(self):
        return [
            MarketSnapshot(
                market_ticker='TEST',
                yes_price=Decimal('0.52'),
                source='rest'
            )
        ]

async def test_get_markets(test_client):
    app.dependency_overrides[get_market_repo] = lambda: MockMarketRepo()
    response = await test_client.get('/api/v1/markets')
    assert response.status_code == 200
    assert len(response.json()) == 1
```

---

### ADR-003: Phase 2-Ready Data Models ⭐

**Decision**: Add `source`, `sequence`, and timezone-aware timestamps in Phase 1 models

**Problem**: Phase 2 will add WebSocket data source. Should we prepare the schema now?

**Analysis**:
- **Cost to add now**: 30 minutes (extra fields in Pydantic + SQLAlchemy)
- **Cost to add later**: 8 hours (Alembic migration + data backfill + testing)
- **Storage overhead**: Negligible (~12 bytes per row)

**Solution**: Add Phase 2 fields now with Phase 1 defaults

```python
# models/domain.py
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Literal, Optional

class MarketSnapshot(BaseModel):
    """Market snapshot with Phase 2-ready fields"""

    market_ticker: str
    yes_price: Decimal
    no_price: Decimal
    volume: int

    # Phase 2-ready fields (ADR-003)
    source: Literal['rest', 'websocket'] = 'rest'  # Phase 1: always 'rest'
    sequence: Optional[int] = None                 # Phase 1: None, Phase 2: WebSocket seq
    timestamp: datetime                            # Timezone-aware (TIMESTAMPTZ)

    raw_data: Optional[dict] = None

    class Config:
        orm_mode = True
```

```python
# models/database.py
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

class DataSource(str, enum.Enum):
    REST = 'rest'
    WEBSOCKET = 'websocket'  # Phase 2

class MarketSnapshotModel(Base):
    __tablename__ = 'market_snapshots'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    market_ticker = Column(String, nullable=False, index=True)

    yes_price = Column(Numeric(10, 4), nullable=False)
    no_price = Column(Numeric(10, 4), nullable=False)
    volume = Column(Integer, nullable=False)

    # Phase 2-ready fields (ADR-003)
    source = Column(Enum(DataSource), nullable=False, default=DataSource.REST)
    sequence = Column(Integer, nullable=True)  # WebSocket gap detection
    timestamp = Column(DateTime(timezone=True), nullable=False)  # TIMESTAMPTZ

    raw_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_ticker_timestamp', 'market_ticker', 'timestamp'),
    )
```

**Phase 1 Usage**:
```python
# Always uses 'rest' source, sequence is None
snapshot = MarketSnapshot(
    market_ticker='INXD-24DEC31',
    yes_price=Decimal('0.52'),
    no_price=Decimal('0.48'),
    volume=15000,
    source='rest',        # Always 'rest' in Phase 1
    sequence=None,        # None in Phase 1
    timestamp=datetime.now(UTC)
)
```

**Phase 2 Transition** (No Migration!):
```python
# WebSocket poller adds to same table
snapshot = MarketSnapshot(
    market_ticker='INXD-24DEC31',
    yes_price=Decimal('0.53'),
    source='websocket',   # Now using WebSocket
    sequence=12345,       # WebSocket sequence number
    timestamp=datetime.fromisoformat(ws_msg['timestamp'])
)
```

**Benefits**:
- ✅ **No schema migration** needed for Phase 2
- ✅ **Gap detection** ready (WebSocket sequence numbers)
- ✅ **Data provenance** (can filter by source for debugging)
- ✅ **Timezone safety** (no naive datetime issues)

**Storage Cost**: ~12 bytes per row (negligible)

---

## Data Models

### Domain Model (Pydantic)

```python
# models/domain.py
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

class MarketSnapshot(BaseModel):
    """Market snapshot for backtesting and analysis"""

    id: UUID
    market_ticker: str = Field(..., description="Kalshi market ticker")

    yes_price: Decimal = Field(..., ge=0, le=1, description="YES price (0-1)")
    no_price: Decimal = Field(..., ge=0, le=1, description="NO price (0-1)")
    volume: int = Field(..., ge=0, description="Total volume traded")

    source: Literal['rest', 'websocket'] = 'rest'
    sequence: Optional[int] = None
    timestamp: datetime

    raw_data: Optional[dict] = None
    created_at: datetime

    def implied_probability(self) -> Decimal:
        """Calculate implied probability from yes_price"""
        return self.yes_price

    class Config:
        orm_mode = True
```

### API Response Models

```python
# models/responses.py
from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime

class MarketResponse(BaseModel):
    """API response for market data"""
    market_ticker: str
    yes_price: Decimal
    no_price: Decimal
    volume: int
    timestamp: datetime

    @classmethod
    def from_orm(cls, snapshot: MarketSnapshot):
        return cls(
            market_ticker=snapshot.market_ticker,
            yes_price=snapshot.yes_price,
            no_price=snapshot.no_price,
            volume=snapshot.volume,
            timestamp=snapshot.timestamp
        )
```

---

## Frontend Architecture

### Technology Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Data Fetching**: Tanstack Query (NOT Apollo/GraphQL)
- **UI Components**: shadcn/ui (TailwindCSS-based)
- **Charts**: Recharts

### Directory Structure

```
frontend/src/
├── api/
│   ├── client.ts            # Axios/fetch client
│   └── queries.ts           # Tanstack Query hooks
│
├── components/
│   ├── markets/
│   │   ├── MarketsPage.tsx  # Main market browser
│   │   ├── MarketCard.tsx   # Individual market display
│   │   └── MarketChart.tsx  # Historical price chart (Recharts)
│   └── ui/                  # shadcn/ui components
│       ├── button.tsx
│       ├── card.tsx
│       └── table.tsx
│
├── hooks/
│   ├── useMarkets.ts        # Fetch all markets
│   └── useMarketHistory.ts  # Fetch historical data
│
├── types/
│   └── api.ts               # TypeScript types (mirrors backend)
│
├── App.tsx
└── main.tsx
```

### Data Fetching Pattern

```typescript
// hooks/useMarkets.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { Market } from '../types/api';

export function useMarkets() {
  return useQuery<Market[]>({
    queryKey: ['markets'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/markets');
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10s (2x poller interval)
  });
}
```

```typescript
// components/markets/MarketsPage.tsx
import { useMarkets } from '../../hooks/useMarkets';
import { MarketCard } from './MarketCard';

export function MarketsPage() {
  const { data: markets, isLoading, error } = useMarkets();

  if (isLoading) return <div>Loading markets...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div className="grid grid-cols-3 gap-4">
      {markets?.map(market => (
        <MarketCard key={market.market_ticker} market={market} />
      ))}
    </div>
  );
}
```

**Why Tanstack Query (not Apollo)?**
- ✅ Simpler for REST APIs (no GraphQL complexity)
- ✅ Better caching control
- ✅ Smaller bundle size
- ✅ Easy migration to GraphQL in Phase 4 if needed

---

## Database Schema

### PostgreSQL Tables

```sql
-- Market snapshots (5s polling data)
CREATE TABLE market_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_ticker VARCHAR NOT NULL,

    yes_price NUMERIC(10, 4) NOT NULL,
    no_price NUMERIC(10, 4) NOT NULL,
    volume INTEGER NOT NULL,

    source VARCHAR NOT NULL DEFAULT 'rest',  -- 'rest' or 'websocket'
    sequence INTEGER,                        -- WebSocket sequence (Phase 2)
    timestamp TIMESTAMPTZ NOT NULL,

    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ix_ticker_timestamp ON market_snapshots (market_ticker, timestamp DESC);
CREATE INDEX ix_source ON market_snapshots (source);
```

```sql
-- Backtest results (from Jupyter notebooks)
CREATE TABLE backtest_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name VARCHAR NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,

    total_pnl NUMERIC(15, 2) NOT NULL,
    sharpe_ratio NUMERIC(10, 4),
    max_drawdown NUMERIC(10, 4),
    win_rate NUMERIC(5, 4),
    total_trades INTEGER NOT NULL,

    equity_curve JSONB NOT NULL,  -- [{date, value}]
    trades JSONB NOT NULL,        -- [{entry, exit, pnl}]

    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Alembic Migrations

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial schema with Phase 2-ready fields"

# Apply migration
alembic upgrade head
```

---

## Deployment (Docker Compose)

### docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: kalshi_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD:-postgres}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  poller:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: python -m poller.main
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD:-postgres}@db:5432/kalshi_db
      - KALSHI_API_KEY=${KALSHI_API_KEY}
      - KALSHI_API_BASE=https://demo-api.kalshi.com
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD:-postgres}@db:5432/kalshi_db
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app  # Hot reload for development

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    command: npm run dev -- --host
    environment:
      - VITE_API_URL=http://localhost:8000
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
      - /app/node_modules

volumes:
  postgres_data:
```

### Environment Variables

```bash
# .env
DB_PASSWORD=postgres
KALSHI_API_KEY=your_kalshi_api_key_here
```

### Quick Start

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f poller  # Watch polling activity
docker-compose logs -f api     # Watch API requests

# Stop all services
docker-compose down
```

**Access Points**:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000/docs
- PostgreSQL: localhost:5432

---

## Testing Strategy

### Unit Tests (pytest)

```python
# tests/test_domain_models.py
from models.domain import MarketSnapshot
from decimal import Decimal

def test_implied_probability():
    snapshot = MarketSnapshot(
        market_ticker='TEST',
        yes_price=Decimal('0.65'),
        no_price=Decimal('0.35'),
        volume=1000,
        source='rest',
        timestamp=datetime.now(UTC)
    )
    assert snapshot.implied_probability() == Decimal('0.65')
```

```python
# tests/test_repositories.py
async def test_market_repo_save_and_retrieve(test_db_session):
    repo = PostgresMarketRepository(test_db_session)

    snapshot = MarketSnapshot(
        market_ticker='TEST',
        yes_price=Decimal('0.52'),
        source='rest',
        timestamp=datetime.now(UTC)
    )
    await repo.save(snapshot)

    retrieved = await repo.get_latest('TEST')
    assert retrieved.market_ticker == 'TEST'
    assert retrieved.yes_price == Decimal('0.52')
```

### Integration Tests

```python
# tests/test_api_markets.py
from httpx import AsyncClient

async def test_get_markets(test_client: AsyncClient):
    response = await test_client.get('/api/v1/markets')
    assert response.status_code == 200
    assert len(response.json()) > 0

    market = response.json()[0]
    assert 'market_ticker' in market
    assert 'yes_price' in market
```

---

## Phase 1 → Phase 2 Transition

### How ADRs Enable Smooth Transition

#### Adding WebSocket (3-5 days effort)

**Step 1: Update Poller (Same Container)**
```python
# poller/main.py
async def main():
    # Keep existing REST polling
    asyncio.create_task(poll_rest_markets())

    # Add WebSocket listener (NEW)
    asyncio.create_task(listen_websocket())

async def listen_websocket():
    async with KalshiWebSocket() as ws:
        async for msg in ws.subscribe('ticker'):
            snapshot = MarketSnapshot(
                market_ticker=msg['ticker'],
                yes_price=Decimal(msg['yes_price']) / 100,
                source='websocket',  # NEW: use 'websocket' source
                sequence=msg['seq'],  # NEW: populate sequence
                timestamp=datetime.fromisoformat(msg['ts'])
            )
            await repo.save(snapshot)
```

**Step 2: Update Frontend (Real-Time UI)**
```typescript
// hooks/useMarketLive.ts
import { useQuery } from '@tanstack/react-query';

export function useMarketLive(ticker: string) {
  return useQuery({
    queryKey: ['market-live', ticker],
    queryFn: async () => {
      const response = await apiClient.get(`/api/v1/markets/${ticker}/latest`);
      return response.data;
    },
    refetchInterval: 1000,  // 1s for "real-time" feel
  });
}
```

**No Breaking Changes**:
- ✅ Database schema already supports `source='websocket'` (ADR-003)
- ✅ Poller is separate container, API untouched (ADR-001)
- ✅ Repository pattern abstracts data source (ADR-002)

---

## Success Criteria Checklist

### Phase 1 Complete When:

**Infrastructure**:
- [ ] Docker Compose runs 3 containers (DB, Poller, API)
- [ ] Poller collects market data every 5 seconds
- [ ] PostgreSQL stores snapshots with `source='rest'`
- [ ] Frontend displays markets via Tanstack Query

**Architecture**:
- [ ] ADR-001: Separate poller container implemented
- [ ] ADR-002: Repository pattern with Protocol interfaces
- [ ] ADR-003: Data models include source/sequence/timestamp fields

**Data Science**:
- [ ] Jupyter notebook connects to PostgreSQL
- [ ] Historical data query works (≥100 snapshots per market)
- [ ] Backtesting framework integrated (backtrader/vectorbt)
- [ ] ≥1 strategy backtested with Sharpe ratio >0.5

**Quality**:
- [ ] Unit tests for domain models (pytest)
- [ ] Integration tests for API endpoints
- [ ] Type checking passes (mypy + TypeScript strict)
- [ ] Pre-commit hooks configured (Ruff, ESLint)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Kalshi API rate limits | Poller stops | Exponential backoff retry (3 attempts) |
| Database connection pool exhaustion | API errors | Set `max_connections=20`, monitor pool usage |
| Poller failure | Data gaps | Health check endpoint, restart policy in docker-compose |
| Poor backtest performance | Wasted effort | Quick validation with simple strategy first |

---

## Next Steps After Phase 1

### Phase 2 Decision Gate

**IF** Phase 1 backtest shows Sharpe ratio >0.5:
- ✅ Add WebSocket to poller container (3-5 days effort)
- ✅ Build live order book visualization
- ✅ Real-time strategy monitoring dashboard

**IF** Phase 1 backtest fails (Sharpe <0.5):
- ❌ Do NOT build WebSocket infrastructure
- ✅ Iterate on strategy in notebooks
- ✅ Validate with more historical data

**The three ADRs ensure Phase 2 transition is smooth IF needed**

---

## Appendix: Technology Justifications

### Why FastAPI over Flask/Django?
- ✅ Async support (better for I/O-bound Kalshi API calls)
- ✅ Automatic OpenAPI docs (`/docs`)
- ✅ Pydantic validation built-in
- ✅ Modern Python 3.11+ features

### Why Separate Poller Container? (ADR-001)
- ✅ GCP Cloud Run auto-scaling safety (Phase 3)
- ✅ Failure isolation (poller crash ≠ API downtime)
- ✅ Independent deployment and scaling
- ✅ 1 hour now vs. 2 weeks refactoring later

### Why Repository Pattern? (ADR-002)
- ✅ Testability (easy to mock)
- ✅ Flexibility (swap PostgreSQL → TimescaleDB)
- ✅ Separation (domain logic independent of infrastructure)

### Why Phase 2-Ready Models? (ADR-003)
- ✅ No schema migration needed for WebSocket (Phase 2)
- ✅ 30 minutes now vs. 8 hours later
- ✅ Minimal storage overhead (~12 bytes per row)

### Why PostgreSQL over SQLite?
- ✅ Production-ready from day 1
- ✅ Direct path to GCP Cloud SQL (Phase 3)
- ✅ JSONB for flexible `raw_data` storage
- ✅ Time-series query optimization

### Why Tanstack Query over Apollo Client?
- ✅ Simpler (no GraphQL in Phase 1)
- ✅ Better caching control
- ✅ Smaller bundle size
- ✅ Easy migration to GraphQL (Phase 4)

---

## Summary

**Phase 1 Architecture**: REST-only polling platform for Kalshi market data and backtesting

**Key Principles**:
- ✅ Simple, proven technologies (REST, PostgreSQL, React)
- ✅ Three critical ADRs provide Phase 2 readiness (~1.5 hours total effort)
- ✅ Focus on offline backtesting, not live trading
- ✅ Prove strategy value before adding real-time complexity

**Timeline**: 2 weeks to "Backtest ≥1 strategy with Sharpe ratio >0.5"

**Next Steps**: Follow implementation checklist, build Phase 1 foundation, validate strategy effectiveness
