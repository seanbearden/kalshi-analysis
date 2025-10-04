# Data Models and Database Schema

## Enhanced Database Models (Phase 2-Ready)

### 1. MarketSnapshot

**Purpose:** Store timestamped market data for historical analysis and backtesting

**SQLAlchemy Model:**
```python
from datetime import datetime, UTC
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

    # Timestamp (timezone-aware TIMESTAMPTZ for market hours)
    timestamp: Mapped[datetime] = mapped_column(index=True)

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
- `source`: Enables debugging (poll vs WebSocket data)
- `sequence`: Allows gap detection in Phase 2 WebSocket streams
- `raw_data`: Preserves full API response for unforeseen analysis needs
- Unique constraint prevents duplicate snapshots
- Composite index optimizes time-range queries

---

### 2. BacktestResult

**Purpose:** Store backtest execution results with full audit trail

**SQLAlchemy Model:**
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

---

### 3. BacktestExecution (Trade-Level Detail)

**Purpose:** Audit trail for individual trades in a backtest

**SQLAlchemy Model:**
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
- `strategy_version`: Enables comparing v1 vs v2 performance
- `BacktestExecution`: Provides audit trail for debugging bad trades
- Foreign keys link to exact `MarketSnapshot` data (reproducibility)
- `signal_metadata`: Stores reasoning (e.g., `{"reason": "price_spike", "threshold": 0.05}`)

---

## Pydantic Models (API Validation)

### KalshiMarket (External API Response)

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

---

### API Request/Response Schemas

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

## Database Indexes

**Optimized for Common Queries:**

1. **Time-range queries** (backtesting):
   - `idx_ticker_timestamp` on `(ticker, timestamp)`

2. **Latest snapshot lookup**:
   - `idx_ticker` on `ticker`
   - `idx_timestamp` on `timestamp DESC`

3. **Backtest lookup**:
   - `idx_strategy_name` on `strategy_name`
   - `idx_backtest_id` on `backtest_id` (for executions)

4. **Data source debugging**:
   - `idx_source` on `source`

---

## Alembic Migrations

**Initial Migration (001_initial_schema.py):**
- Create `market_snapshots` table with all fields
- Create `backtest_results` table
- Create `backtest_executions` table with foreign keys
- Create all indexes and unique constraints

**Phase 2 Migration (future):**
- No schema changes needed (already has `source`, `sequence` fields)
- Add index on `sequence` for gap detection optimization
