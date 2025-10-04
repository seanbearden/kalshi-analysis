# Phase 1 Implementation Plan

## Week 1: Foundation (Must Build First)

### Day 1-2: Core Infrastructure
1. **Directory structure** (infrastructure/, domain/, schemas/)
   - Create all necessary folders
   - Add `__init__.py` files
   
2. **Separate poller container** (CRITICAL)
   - Extract `poller.py` as standalone script
   - Create docker-compose with `poller` + `api` services
   - Test: Run 3 API instances → verify single poller runs

3. **Production essentials**
   - Health check endpoint (`/api/v1/health`)
   - Global exception handler
   - Rate limiting with slowapi
   - Structured logging configuration

### Day 3: Data Models
4. **Enhanced database models**
   - MarketSnapshot with `source`, `sequence`, `id` fields
   - BacktestResult with `strategy_version`
   - BacktestExecution for trade-level audit
   - Write Alembic migration

5. **Pydantic models**
   - KalshiMarket schema (external API validation)
   - API request/response schemas
   - Configuration with Pydantic Settings

## Week 2: Core Features

### Day 4-5: Data Access Layer
6. **Repository pattern**
   - MarketSnapshotRepository with Protocol
   - BacktestRepository for results
   - SQLAlchemy implementations
   - Update services to use repositories

### Day 6: External Integration
7. **Kalshi client resilience**
   - httpx async client
   - Retry logic with tenacity (3 attempts, exponential backoff)
   - Connection pooling
   - Timeout strategy (10s total, 5s connect)

### Day 7-8: API Implementation
8. **FastAPI application**
   - `api/main.py` with lifespan management
   - Dependency injection (`api/deps.py`)
   - Routes:
     - GET `/api/v1/health`
     - GET `/api/v1/markets` (list with filtering)
     - GET `/api/v1/markets/{ticker}` (details)
     - GET `/api/v1/markets/{ticker}/snapshots` (time range)
     - POST `/api/v1/backtests` (run backtest)
     - GET `/api/v1/backtests/{id}` (results)

### Day 9: Dependencies
9. **requirements.txt and pyproject.toml**
   - Production dependencies (fastapi, pydantic, sqlalchemy, etc.)
   - Development dependencies (pytest, mypy, ruff, black)
   - Tool configurations (mypy, ruff, black)

## Week 3: Integration

### Day 10-11: Containerization
10. **Docker configuration**
    - Dockerfile (API container)
    - Dockerfile.poller (poller container)
    - docker-compose.yml (postgres + poller + api)
    - .env.example (all environment variables)

### Day 12: Database Migrations
11. **Alembic setup**
    - alembic.ini configuration
    - env.py for async migrations
    - Initial migration (001_initial_schema.py)
    - Test: `alembic upgrade head`

### Day 13-14: Background Tasks
12. **Standalone poller implementation**
    - 5-second polling loop
    - Graceful shutdown handling
    - Error recovery with exponential backoff
    - Test: Verify singleton behavior

### Day 15: Jupyter Integration
13. **Notebook integration**
    - Example notebook for strategy development
    - API client wrapper for notebooks
    - Backtesting workflow documentation

## Phase 1 Completion Checklist

**Backend:**
- [ ] FastAPI server with `/api/v1/*` endpoints
- [ ] Kalshi API client with 5s polling loop
- [ ] PostgreSQL models for market snapshots
- [ ] Pydantic models for type safety
- [ ] Docker Compose setup with separate poller container
- [ ] Health check endpoint working
- [ ] Rate limiting configured
- [ ] Repository pattern implemented

**Frontend:**
- [ ] React app with Tanstack Query
- [ ] shadcn/ui DataTable displaying markets
- [ ] Basic Recharts visualization
- [ ] Environment configuration

**Data Science:**
- [ ] Jupyter notebook for Kalshi data exploration
- [ ] Backtesting framework integration (backtrader/vectorbt)
- [ ] At least 1 strategy with Sharpe >0.5
- [ ] Reliability diagram component

**DevOps:**
- [ ] `make demo` command working
- [ ] Pre-commit hooks configured
- [ ] README reflects actual Phase 1 scope
- [ ] Docker images build successfully
- [ ] Alembic migrations working

## Success Metrics

**Technical:**
- API latency <100ms p95
- Polling reliability >99% uptime
- Database query <50ms p95
- Backtest execution <10s for 1000 snapshots

**Business:**
- At least 1 backtested strategy with Sharpe >0.5
- Portfolio-quality documentation
- Clean architecture demonstrating engineering discipline

## Deferred to Future Phases

**Phase 2:**
- WebSocket streaming
- Real-time order book visualization
- Live strategy performance dashboard

**Phase 3:**
- Event-driven trade execution
- GCP deployment (Cloud Run + Cloud SQL)
- Monitoring and alerting

**Phase 4:**
- GraphQL layer (Strawberry)
- User authentication
- Redis caching
- Horizontal scaling
