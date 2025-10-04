# Critical Architecture Decisions

## ADR-001: Separate Poller Container (CRITICAL)

**Status:** Accepted
**Date:** 2025-10-03
**Priority:** HIGH - Must implement in Week 1

### Problem
Background polling can be implemented in FastAPI lifespan or as separate container.

**Anti-Pattern (DO NOT USE):**
```python
# WRONG: Poller in FastAPI lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    poller = MarketPoller()  # Runs in EVERY worker process
    await poller.start()     # Multiple uvicorn workers = duplicate polling
```

**Why this breaks Phase 3 (GCP):**
- Cloud Run auto-scales to multiple instances → each runs poller → rate limit violations
- No coordination between instances → duplicate data writes
- Requires complete architectural refactor to fix

### Solution
Extract poller as separate Docker container from day 1.

```yaml
# docker-compose.yml
services:
  poller:   # Singleton - always 1 instance
    build: ./backend
    command: python -m infrastructure.polling.poller

  api:      # Scales horizontally - N instances
    build: ./backend
    command: uvicorn api.main:app
```

### Rationale
- **Multi-instance safety:** GCP auto-scaling won't create duplicate pollers
- **Independent scaling:** API scales on traffic, poller runs at constant rate
- **Failure isolation:** Poller crash doesn't affect API
- **Deployment flexibility:** Can deploy poller updates independently

### Implementation Cost
- 1 hour now vs. 2 weeks refactoring in Phase 3

---

## ADR-002: Repository Pattern

**Status:** Accepted
**Date:** 2025-10-03

### Decision
Implement repository pattern with Protocol interfaces for data access layer.

### Rationale
- **Testability:** Easy to mock for unit tests
- **Flexibility:** Can swap PostgreSQL → TimescaleDB without changing business logic
- **Separation:** Domain logic doesn't depend on infrastructure details

### Example
```python
# Protocol (interface)
class MarketSnapshotRepository(Protocol):
    async def get_latest(self, ticker: str) -> MarketSnapshot | None: ...
    async def save(self, snapshot: MarketSnapshot) -> None: ...

# Implementation
class SQLAlchemyMarketRepo:
    def __init__(self, session: AsyncSession):
        self.session = session
```

---

## ADR-003: Phase 2 Data Model Preparation

**Status:** Accepted
**Date:** 2025-10-03

### Decision
Add `source`, `sequence`, and timezone-aware timestamps in Phase 1 models.

### Enhanced MarketSnapshot Schema
```python
class MarketSnapshot:
    id: UUID                          # ✅ Added
    ticker: str
    timestamp: datetime               # ✅ Timezone-aware (TIMESTAMPTZ)
    source: DataSource                # ✅ "poll" | "websocket" | "backfill"
    sequence: int | None              # ✅ WebSocket gap detection
    yes_price: Decimal
    no_price: Decimal
    volume: int
    raw_data: dict
    created_at: datetime
```

### Rationale
- **Forward compatibility:** No schema migration needed for Phase 2
- **Debugging:** `source` field helps identify data provenance
- **Minimal cost:** Extra columns have negligible storage impact

---

## ADR-004: PostgreSQL First (No Redis in Phase 1)

**Status:** Accepted
**Date:** 2025-10-03

### Decision
Use PostgreSQL only for Phase 1, defer Redis to Phase 3+.

### Rationale
- **Simplicity:** One database to manage
- **Sufficient performance:** Single-user local tool doesn't need caching
- **YAGNI:** Premature optimization

### Future Addition (Phase 3+)
Redis can be added as caching layer without code changes due to repository pattern abstraction.

---

## Directory Structure (Improved)

**Rationale:** Clear separation of concerns, easy navigation for developers learning FastAPI

```
backend/
├── api/                    # HTTP Layer (thin controllers)
│   ├── main.py            # FastAPI app, lifespan, middleware
│   ├── deps.py            # Dependency injection
│   └── v1/                # Explicit API versioning
│       ├── markets.py
│       ├── backtests.py
│       └── health.py
│
├── domain/                 # Business Logic (pure Python, no framework deps)
│   ├── market.py          # implied_probability(), analytics
│   └── strategy.py        # signal evaluation
│
├── infrastructure/         # External Systems Integration
│   ├── kalshi/
│   │   ├── client.py      # httpx async client with retry logic
│   │   └── schemas.py     # Pydantic models for Kalshi API
│   ├── database/
│   │   ├── models.py      # SQLAlchemy models
│   │   └── repositories.py # Data access layer
│   └── polling/
│       └── poller.py      # Standalone script (separate container)
│
├── schemas/                # API Contracts
│   ├── requests.py        # API input validation
│   └── responses.py       # API output contracts
│
├── core/                   # Cross-cutting Concerns
│   ├── config.py          # Pydantic Settings
│   ├── database.py        # SQLAlchemy engine, session factory
│   └── logging.py         # Structured logging
│
└── alembic/               # Database Migrations
```

---

## Production Essentials (Phase 1)

### Required for GCP Deployment

1. **Health Check Endpoint** (`/health`)
   - Required for GCP load balancer probes
   - Checks database connectivity

2. **Global Exception Handler**
   - Prevents raw 500 errors
   - Returns structured JSON errors

3. **Rate Limiting**
   - Protects against Kalshi API abuse
   - Default: 10 requests/minute per IP

4. **Structured Logging**
   - JSON format for GCP Cloud Logging
   - Includes request IDs, user context

5. **Retry Logic**
   - Kalshi API client uses tenacity
   - 3 attempts with exponential backoff (2s, 4s, 8s)
