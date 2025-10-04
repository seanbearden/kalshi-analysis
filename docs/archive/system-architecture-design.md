# Kalshi Market Insights - System Architecture Design

## Executive Summary

**Project Type**: Portfolio-quality quantitative trading platform
**Current Phase**: Phase 1 - Local Analytics Workbench (2-week MVP)
**Architecture Style**: Phased evolution from single-user local tool → production SaaS
**Key Principle**: Prove value before adding complexity

---

## System Context Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     External Systems                            │
│                                                                 │
│  ┌──────────────────┐              ┌──────────────────┐       │
│  │   Kalshi API     │              │  User's Browser  │       │
│  │  (REST + WS)     │              │   (localhost)    │       │
│  └────────┬─────────┘              └────────┬─────────┘       │
└───────────┼──────────────────────────────────┼─────────────────┘
            │                                  │
            │ HTTP/WebSocket                   │ HTTP
            │                                  │
┌───────────▼──────────────────────────────────▼─────────────────┐
│                Kalshi Market Insights Platform                  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   Poller     │  │  FastAPI     │  │    React Frontend    │ │
│  │  Container   │  │   Backend    │  │   (Vite + TS)        │ │
│  │              │  │              │  │                      │ │
│  │  • Polls     │  │  • REST API  │  │  • Market Browser   │ │
│  │    every 5s  │  │  • Business  │  │  • Backtest Viewer  │ │
│  │  • Stores    │  │    Logic     │  │  • Charts           │ │
│  │    snapshots │  │  • Data      │  │                      │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘ │
│         │                 │                                     │
│         └────────┬────────┘                                     │
│                  │                                              │
│         ┌────────▼────────┐                                     │
│         │   PostgreSQL    │                                     │
│         │                 │                                     │
│         │  • Market       │                                     │
│         │    Snapshots    │                                     │
│         │  • Backtest     │                                     │
│         │    Results      │                                     │
│         └─────────────────┘                                     │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Jupyter Notebooks (Local)                    │  │
│  │  • Strategy Development  • Data Analysis  • Backtesting  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Phase 1 Component Architecture

### 1. Poller Container (Critical Design Decision)

**Why Separate Container?**
- ✅ GCP Cloud Run auto-scaling won't duplicate polling
- ✅ Independent scaling (API scales on traffic, poller runs constant)
- ✅ Failure isolation (poller crash ≠ API downtime)
- ✅ Deployment flexibility (update poller without API restart)

**Implementation**:
```python
# infrastructure/polling/poller.py
import asyncio
from kalshi_client import KalshiClient
from database.repositories import MarketSnapshotRepository

async def poll_markets():
    client = KalshiClient(api_key=settings.KALSHI_API_KEY)
    repo = MarketSnapshotRepository(db_session)

    while True:
        markets = await client.get_markets(status='active')

        for market in markets:
            snapshot = MarketSnapshot(
                ticker=market['ticker'],
                timestamp=datetime.now(UTC),
                source='poll',  # Phase 2: 'websocket' | 'backfill'
                yes_price=market['yes_price'],
                no_price=market['no_price'],
                volume=market['volume']
            )
            await repo.save(snapshot)

        await asyncio.sleep(5)  # 5-second interval

if __name__ == '__main__':
    asyncio.run(poll_markets())
```

**Docker Compose**:
```yaml
services:
  poller:
    build: ./backend
    command: python -m infrastructure.polling.poller
    depends_on:
      - db
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - KALSHI_API_KEY=${KALSHI_API_KEY}

  api:
    build: ./backend
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: kalshi_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

---

### 2. FastAPI Backend Architecture

**Layered Architecture Pattern**:

```
┌─────────────────────────────────────────┐
│         API Layer (HTTP)                │
│  • Request validation (Pydantic)        │
│  • Response serialization               │
│  • Error handling                       │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│         Domain Layer                    │
│  • Business logic (pure Python)         │
│  • Strategy evaluation                  │
│  • Probability calculations             │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│      Infrastructure Layer               │
│  • Kalshi API client                    │
│  • Database repositories                │
│  • External integrations                │
└─────────────────────────────────────────┘
```

**Directory Structure**:
```
backend/
├── api/                      # HTTP Layer
│   ├── main.py              # FastAPI app, CORS, middleware
│   ├── deps.py              # Dependency injection
│   └── v1/                  # API version 1
│       ├── markets.py       # GET /api/v1/markets
│       ├── backtests.py     # GET /api/v1/backtests, POST /api/v1/backtests
│       └── health.py        # GET /health (for GCP health checks)
│
├── domain/                   # Business Logic
│   ├── market.py            # implied_probability(), kelly_criterion()
│   └── strategy.py          # signal_evaluation(), risk_metrics()
│
├── infrastructure/
│   ├── kalshi/
│   │   ├── client.py        # Async httpx client with retry
│   │   └── schemas.py       # Pydantic models for Kalshi responses
│   ├── database/
│   │   ├── models.py        # SQLAlchemy ORM models
│   │   └── repositories.py # Repository pattern implementations
│   └── polling/
│       └── poller.py        # Standalone polling script
│
├── schemas/                  # API Contracts
│   ├── requests.py          # BacktestRequest, MarketFilter
│   └── responses.py         # MarketResponse, BacktestResult
│
├── core/                     # Cross-cutting
│   ├── config.py            # Pydantic Settings (env vars)
│   ├── database.py          # SQLAlchemy engine, session
│   └── logging.py           # Structured JSON logging
│
└── alembic/                 # Database migrations
    └── versions/
```

**API Endpoints (Phase 1)**:

```python
# api/v1/markets.py
from fastapi import APIRouter, Depends
from schemas.responses import MarketResponse

router = APIRouter(prefix='/markets', tags=['markets'])

@router.get('/', response_model=list[MarketResponse])
async def get_markets(
    repo: MarketSnapshotRepository = Depends(get_market_repo)
):
    """Get latest snapshot for all active markets"""
    snapshots = await repo.get_all_latest()
    return [MarketResponse.from_orm(s) for s in snapshots]

@router.get('/{ticker}/history', response_model=list[MarketResponse])
async def get_market_history(
    ticker: str,
    repo: MarketSnapshotRepository = Depends(get_market_repo)
):
    """Get historical snapshots for specific market"""
    snapshots = await repo.get_history(ticker, limit=100)
    return [MarketResponse.from_orm(s) for s in snapshots]
```

```python
# api/v1/backtests.py
from fastapi import APIRouter, Depends
from schemas.requests import BacktestRequest
from schemas.responses import BacktestResult

router = APIRouter(prefix='/backtests', tags=['backtests'])

@router.post('/', response_model=BacktestResult)
async def run_backtest(
    request: BacktestRequest,
    repo: BacktestRepository = Depends(get_backtest_repo)
):
    """Execute backtest strategy on historical data"""
    result = await backtest_service.run(request)
    await repo.save(result)
    return BacktestResult.from_orm(result)

@router.get('/', response_model=list[BacktestResult])
async def get_backtests(
    repo: BacktestRepository = Depends(get_backtest_repo)
):
    """List all backtest results"""
    results = await repo.get_all()
    return [BacktestResult.from_orm(r) for r in results]
```

**Repository Pattern (Testability + Flexibility)**:

```python
# infrastructure/database/repositories.py
from typing import Protocol
from sqlalchemy.ext.asyncio import AsyncSession

class MarketSnapshotRepository(Protocol):
    async def get_latest(self, ticker: str) -> MarketSnapshot | None: ...
    async def get_all_latest(self) -> list[MarketSnapshot]: ...
    async def save(self, snapshot: MarketSnapshot) -> None: ...

class SQLAlchemyMarketRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all_latest(self) -> list[MarketSnapshot]:
        """Get latest snapshot for each unique ticker"""
        stmt = (
            select(MarketSnapshotModel)
            .distinct(MarketSnapshotModel.ticker)
            .order_by(
                MarketSnapshotModel.ticker,
                MarketSnapshotModel.timestamp.desc()
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
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
    return SQLAlchemyMarketRepo(session)
```

---

### 3. React Frontend Architecture

**Technology Choices**:
- **Data Fetching**: Tanstack Query (NOT Apollo/GraphQL in Phase 1)
- **UI Components**: shadcn/ui (TailwindCSS-based)
- **Charts**: Recharts (simple, bundle-efficient)
- **State**: React Query + local useState (no Redux/Zustand needed)

**Component Structure**:
```
frontend/src/
├── components/
│   ├── markets/
│   │   ├── MarketsPage.tsx       # Main market browser
│   │   ├── MarketCard.tsx        # Individual market display
│   │   └── MarketChart.tsx       # Price history chart
│   ├── backtests/
│   │   ├── BacktestsPage.tsx     # Backtest results viewer
│   │   ├── BacktestCard.tsx      # Summary card (PnL, Sharpe, etc.)
│   │   └── BacktestChart.tsx     # Equity curve visualization
│   └── ui/                        # shadcn/ui components
│       ├── button.tsx
│       ├── card.tsx
│       └── chart.tsx
│
├── lib/
│   ├── api.ts                     # Axios/fetch client
│   └── queryClient.ts             # Tanstack Query config
│
├── hooks/
│   ├── useMarkets.ts              # Fetch markets with React Query
│   └── useBacktests.ts            # Fetch backtests with React Query
│
├── types/
│   └── api.ts                     # TypeScript types (mirrors backend schemas)
│
├── App.tsx                        # Router setup
└── main.tsx                       # Entry point
```

**Data Fetching Pattern (Tanstack Query)**:

```typescript
// hooks/useMarkets.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../lib/api';

export function useMarkets() {
  return useQuery({
    queryKey: ['markets'],
    queryFn: async () => {
      const response = await apiClient.get('/api/v1/markets');
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10s
  });
}

// hooks/useMarketHistory.ts
export function useMarketHistory(ticker: string) {
  return useQuery({
    queryKey: ['market-history', ticker],
    queryFn: async () => {
      const response = await apiClient.get(`/api/v1/markets/${ticker}/history`);
      return response.data;
    },
  });
}
```

**Component Example**:
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
      {markets.map(market => (
        <MarketCard key={market.ticker} market={market} />
      ))}
    </div>
  );
}

// components/markets/MarketCard.tsx
export function MarketCard({ market }: { market: Market }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{market.ticker}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex justify-between">
          <span className="text-green-600">YES: ${market.yes_price}</span>
          <span className="text-red-600">NO: ${market.no_price}</span>
        </div>
        <p className="text-sm text-gray-500">Volume: {market.volume}</p>
      </CardContent>
    </Card>
  );
}
```

---

### 4. Data Models & Database Schema

**Enhanced Schema (Phase 2-Ready)**:

```python
# infrastructure/database/models.py
from sqlalchemy import Column, String, Integer, Numeric, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

class DataSource(str, enum.Enum):
    POLL = 'poll'
    WEBSOCKET = 'websocket'  # Phase 2
    BACKFILL = 'backfill'    # Phase 2+

class MarketSnapshotModel(Base):
    __tablename__ = 'market_snapshots'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)  # TIMESTAMPTZ
    source = Column(Enum(DataSource), nullable=False, default=DataSource.POLL)
    sequence = Column(Integer, nullable=True)  # WebSocket gap detection (Phase 2)

    yes_price = Column(Numeric(10, 2), nullable=False)
    no_price = Column(Numeric(10, 2), nullable=False)
    volume = Column(Integer, nullable=False)

    raw_data = Column(JSONB, nullable=True)  # Store full Kalshi response
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('ix_ticker_timestamp', 'ticker', 'timestamp'),
    )

class BacktestResultModel(Base):
    __tablename__ = 'backtest_results'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    strategy_name = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)

    total_pnl = Column(Numeric(15, 2), nullable=False)
    sharpe_ratio = Column(Numeric(10, 4), nullable=True)
    max_drawdown = Column(Numeric(10, 4), nullable=True)
    win_rate = Column(Numeric(5, 4), nullable=True)
    total_trades = Column(Integer, nullable=False)

    equity_curve = Column(JSONB, nullable=False)  # [{date, value}]
    trades = Column(JSONB, nullable=False)        # [{entry, exit, pnl}]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Pydantic Domain Models**:
```python
# domain/market.py
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from enum import Enum

class DataSource(str, Enum):
    POLL = 'poll'
    WEBSOCKET = 'websocket'
    BACKFILL = 'backfill'

class MarketSnapshot(BaseModel):
    id: UUID4
    ticker: str
    timestamp: datetime
    source: DataSource
    sequence: int | None = None

    yes_price: Decimal
    no_price: Decimal
    volume: int

    raw_data: dict | None = None

    def implied_probability(self) -> Decimal:
        """Calculate implied probability from yes_price"""
        return self.yes_price / Decimal(100)

    class Config:
        orm_mode = True
```

---

### 5. Kalshi API Client

**Retry Logic + Type Safety**:

```python
# infrastructure/kalshi/client.py
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from .schemas import KalshiMarket, KalshiMarketResponse

class KalshiClient:
    def __init__(self, api_key: str, base_url: str = 'https://demo-api.kalshi.com'):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=30.0
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8)  # 2s, 4s, 8s
    )
    async def get_markets(self, status: str = 'active') -> list[KalshiMarket]:
        """Fetch markets with retry logic"""
        response = await self.client.get(
            '/api/v1/markets',
            params={'status': status}
        )
        response.raise_for_status()

        # Validate with Pydantic
        data = KalshiMarketResponse(**response.json())
        return data.markets

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def get_market(self, ticker: str) -> KalshiMarket:
        """Fetch single market"""
        response = await self.client.get(f'/api/v1/markets/{ticker}')
        response.raise_for_status()
        return KalshiMarket(**response.json())
```

**Type-Safe Schemas**:
```python
# infrastructure/kalshi/schemas.py
from pydantic import BaseModel

class KalshiMarket(BaseModel):
    ticker: str
    title: str
    yes_price: int  # Cents
    no_price: int   # Cents
    volume: int
    open_time: datetime
    close_time: datetime
    status: str

class KalshiMarketResponse(BaseModel):
    markets: list[KalshiMarket]
    cursor: str | None = None
```

---

## Production-Ready Features (Phase 1)

### 1. Health Check Endpoint
```python
# api/v1/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=['health'])

@router.get('/health')
async def health_check(db: AsyncSession = Depends(get_db_session)):
    """Health check for GCP load balancer"""
    try:
        # Check database connectivity
        await db.execute('SELECT 1')
        return {'status': 'healthy', 'database': 'connected'}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}
```

### 2. Global Exception Handler
```python
# api/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Prevent raw 500 errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={'error': 'Internal server error', 'detail': str(exc)}
    )
```

### 3. Structured Logging
```python
# core/logging.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName
        }
        return json.dumps(log_data)

# Usage
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

### 4. CORS Configuration
```python
# api/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:5173'],  # Vite dev server
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
```

---

## Deployment Architecture (Docker Compose)

```yaml
# docker-compose.yml
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
    command: python -m infrastructure.polling.poller
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD:-postgres}@db:5432/kalshi_db
      - KALSHI_API_KEY=${KALSHI_API_KEY}
      - KALSHI_API_BASE=${KALSHI_API_BASE:-https://demo-api.kalshi.com}
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
      - KALSHI_API_KEY=${KALSHI_API_KEY}
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
      - ./frontend:/app  # Hot reload for development
      - /app/node_modules

volumes:
  postgres_data:
```

**Environment Variables (.env)**:
```bash
# Database
DB_PASSWORD=postgres

# Kalshi API
KALSHI_API_KEY=your_api_key_here
KALSHI_API_BASE=https://demo-api.kalshi.com

# Frontend
VITE_API_URL=http://localhost:8000
```

---

## Phase Evolution Roadmap

### Phase 1: Local Analytics Workbench ✅ (Current)
**Timeline**: 2 weeks
**Deployment**: Docker Compose (local)
**Features**:
- REST API only (no GraphQL)
- 5-second polling (no WebSocket)
- PostgreSQL for snapshots + backtests
- Jupyter notebooks for strategy development

**Success Criteria**:
- Backtest ≥1 strategy
- Sharpe ratio >0.5
- Clean architecture foundation

---

### Phase 2: Real-Time Monitoring (If Phase 1 validates)
**Additions**:
- WebSocket connection to Kalshi
- Live order book visualization
- Real-time strategy performance dashboard
- Enhanced `MarketSnapshot` with `source='websocket'` and `sequence` fields

**No Breaking Changes**:
- Database schema already prepared (ADR-003)
- Repository pattern allows swap without logic changes

---

### Phase 3: Automated Trading Bot (If strategies profitable)
**Additions**:
- Event-driven trade execution (GCP Cloud Tasks or Celery)
- GCP deployment:
  - Cloud Run (API + Poller as separate services)
  - Cloud SQL (managed PostgreSQL)
  - Secret Manager (API keys)
- Monitoring and alerting (GCP Cloud Logging + Monitoring)

**Architecture Adjustment**:
```yaml
# GCP Cloud Run deployment
services:
  api:
    image: gcr.io/project/kalshi-api
    env:
      DATABASE_URL: ${CLOUD_SQL_CONNECTION}
      KALSHI_API_KEY: ${SECRET_MANAGER_KEY}
    scaling:
      min_instances: 1
      max_instances: 10  # Auto-scale on traffic

  poller:
    image: gcr.io/project/kalshi-poller
    env:
      DATABASE_URL: ${CLOUD_SQL_CONNECTION}
    scaling:
      min_instances: 1
      max_instances: 1  # ALWAYS 1 (no duplication)
```

---

### Phase 4: Multi-User SaaS (If market demand exists)
**Additions**:
- User authentication (Firebase Auth)
- GraphQL layer (Strawberry)
- Redis caching
- Horizontal scaling
- Subscription billing (Stripe)

---

## Testing Strategy

### Unit Tests (pytest)
```python
# tests/test_domain_market.py
from domain.market import MarketSnapshot

def test_implied_probability():
    snapshot = MarketSnapshot(
        ticker='TEST',
        yes_price=Decimal('65.00'),
        no_price=Decimal('35.00'),
        volume=1000
    )
    assert snapshot.implied_probability() == Decimal('0.65')
```

### Integration Tests
```python
# tests/test_api_markets.py
from httpx import AsyncClient

async def test_get_markets(client: AsyncClient):
    response = await client.get('/api/v1/markets')
    assert response.status_code == 200
    assert len(response.json()) > 0
```

### Repository Tests (with test database)
```python
# tests/test_repositories.py
async def test_market_repo_save_and_retrieve(test_db_session):
    repo = SQLAlchemyMarketRepo(test_db_session)

    snapshot = MarketSnapshot(ticker='TEST', ...)
    await repo.save(snapshot)

    retrieved = await repo.get_latest('TEST')
    assert retrieved.ticker == 'TEST'
```

---

## Performance Targets (Phase 1)

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time | <100ms | p95 latency |
| Poller Interval | 5 seconds | Consistent polling |
| Database Queries | <50ms | p95 query time |
| Frontend Load Time | <2s | Initial page load |
| Market Snapshots | 100/market | Historical retention |

---

## Security Considerations

### Phase 1 (Local Development)
- API keys in `.env` (not committed)
- Local PostgreSQL (no external access)
- CORS restricted to `localhost:5173`

### Phase 3 (Production GCP)
- Secret Manager for API keys
- Cloud SQL with private IP
- IAM-based service authentication
- Rate limiting (10 req/min per IP)
- SQL injection protection (parameterized queries via SQLAlchemy)

---

## Monitoring & Observability (Phase 3)

### Metrics to Track
- Kalshi API latency (p50, p95, p99)
- Database connection pool usage
- Poller success/failure rate
- API endpoint latency by route

### Logging Strategy
- Structured JSON logs (GCP Cloud Logging format)
- Request IDs for tracing
- Error context (stack traces, user IDs)

### Alerts
- Poller downtime >5 minutes
- Kalshi API errors >10% (5-minute window)
- Database connection failures
- API response time >500ms (p95)

---

## Key Architectural Principles

1. **Phased Complexity**: Prove value before adding features
2. **Separation of Concerns**: Domain logic independent of infrastructure
3. **Type Safety**: Pydantic (backend) + TypeScript (frontend)
4. **Testability**: Repository pattern + dependency injection
5. **Cloud-Ready from Day 1**: Docker, env configs, GCP patterns
6. **Fail-Safe Design**: Poller separation prevents auto-scaling issues

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Kalshi API rate limits | Poller stops | Implement rate limiter, exponential backoff |
| Database connection pool exhaustion | API downtime | Set max connections, monitor pool usage |
| Poller duplication (Phase 3) | Duplicate data | ✅ Separate container from day 1 (ADR-001) |
| WebSocket gaps (Phase 2) | Missing data | `sequence` field for gap detection (ADR-003) |
| Poor backtest performance | Wasted development | Small scope Phase 1, quick validation |

---

## Success Metrics

### Phase 1 MVP Success
- ✅ Backtest ≥1 strategy with Sharpe ratio >0.5
- ✅ Clean architecture foundation (passes code review)
- ✅ <2 week development time
- ✅ Docker deployable with single command

### Phase 2 Decision Criteria
- Phase 1 strategy shows profitability potential
- Real-time data provides trading edge
- User (you) finds value in live monitoring

### Phase 3 Decision Criteria
- Profitable strategy validated
- Willing to invest in GCP costs
- Automated execution justified by returns

---

## Appendix: Technology Justifications

### Why FastAPI over Flask/Django?
- ✅ Async support (better for I/O-bound Kalshi API calls)
- ✅ Automatic OpenAPI docs
- ✅ Pydantic validation built-in
- ✅ Modern Python (3.11+)

### Why Tanstack Query over Apollo Client?
- ✅ Simpler (no GraphQL complexity in Phase 1)
- ✅ Better caching control
- ✅ Smaller bundle size
- ✅ Easy migration to GraphQL in Phase 4

### Why PostgreSQL over SQLite/MongoDB?
- ✅ Production-ready from day 1
- ✅ Direct path to GCP Cloud SQL
- ✅ JSONB for flexible raw_data storage
- ✅ Time-series query optimization

### Why Separate Poller Container?
- ✅ GCP Cloud Run auto-scaling won't duplicate polling
- ✅ Failure isolation (poller crash ≠ API downtime)
- ✅ Independent deployment and scaling
- ✅ **Critical for Phase 3 success** (ADR-001)
