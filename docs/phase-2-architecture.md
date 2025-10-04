# Phase 2 Architecture: Real-Time Monitoring

**Status**: Planned (Conditional on Phase 1 Success)
**Prerequisites**: Phase 1 backtest shows Sharpe ratio >0.5
**Timeline**: 1 week (with Phase 1 ADRs implemented)
**Goal**: Add real-time market monitoring for live strategy execution

---

## Decision Gate

**Phase 2 is ONLY justified if Phase 1 proves strategy profitability**

✅ **Proceed to Phase 2 IF**:
- Phase 1 backtest achieves Sharpe ratio >0.5
- Strategy shows consistent performance across multiple market conditions
- Risk-adjusted returns justify real-time infrastructure investment

❌ **Stay in Phase 1 IF**:
- Backtest performance is poor (Sharpe <0.5)
- Strategy requires more research and iteration
- Focus remains on offline analysis

---

## Architecture Evolution

### Phase 1 → Phase 2 Changes

```
Phase 1 (REST-only):
┌─────────────┐
│   Poller    │ ──5s REST──> Kalshi API
│  Container  │
└─────────────┘

Phase 2 (REST + WebSocket):
┌─────────────────────────┐
│      Poller Container   │
│                         │
│  ┌─────────────────┐    │
│  │  REST Polling   │ ───5s REST──> Kalshi API
│  │  (background)   │    │
│  └─────────────────┘    │
│                         │
│  ┌─────────────────┐    │
│  │  WebSocket      │ ──WebSocket─> Kalshi API
│  │  Listener (NEW) │    │
│  └─────────────────┘    │
└─────────────────────────┘
```

**Key Insight**: Both data sources write to PostgreSQL with `source` field differentiating them

---

## WebSocket Integration

### Poller Container Enhancement

```python
# poller/main.py
import asyncio
from kalshi_client import KalshiRestClient, KalshiWebSocketClient
from repositories.protocols import MarketRepository

async def main():
    """Run both REST polling and WebSocket listener in parallel"""
    repo = get_market_repo()

    # Keep REST polling (backward compatibility, gap filling)
    rest_task = asyncio.create_task(poll_rest_markets(repo))

    # Add WebSocket listener (real-time updates)
    ws_task = asyncio.create_task(listen_websocket(repo))

    await asyncio.gather(rest_task, ws_task)

async def poll_rest_markets(repo: MarketRepository):
    """Existing REST polling (unchanged from Phase 1)"""
    client = KalshiRestClient(api_key=settings.KALSHI_API_KEY)

    while True:
        markets = await client.get_markets(status='active')

        for market in markets:
            snapshot = MarketSnapshot(
                market_ticker=market['ticker'],
                yes_price=Decimal(market['yes_price']) / 100,
                source='rest',  # REST source
                sequence=None,  # No sequence for REST
                timestamp=datetime.now(UTC)
            )
            await repo.save(snapshot)

        await asyncio.sleep(5)

async def listen_websocket(repo: MarketRepository):
    """NEW: WebSocket listener for real-time updates"""
    client = KalshiWebSocketClient(
        api_key=settings.KALSHI_API_KEY,
        endpoint='wss://demo-api.kalshi.co/trade-api/ws/v2'
    )

    async with client.connect() as ws:
        # Subscribe to all active market tickers
        await ws.subscribe({'type': 'ticker', 'market_ticker': '*'})

        async for message in ws:
            if message['type'] == 'ticker':
                snapshot = MarketSnapshot(
                    market_ticker=message['ticker'],
                    yes_price=Decimal(message['yes_price']) / 100,
                    no_price=Decimal(message['no_price']) / 100,
                    volume=message['volume'],
                    source='websocket',  # WebSocket source
                    sequence=message['seq'],  # Sequence for gap detection
                    timestamp=datetime.fromisoformat(message['timestamp'])
                )
                await repo.save(snapshot)
```

### Reconnection Logic

```python
# poller/websocket_client.py
from tenacity import retry, stop_after_attempt, wait_exponential

class KalshiWebSocketClient:
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=30)
    )
    async def connect(self):
        """Connect with exponential backoff retry"""
        try:
            self.ws = await websockets.connect(self.endpoint)
            logger.info('WebSocket connected')
            return self.ws
        except Exception as e:
            logger.error(f'WebSocket connection failed: {e}')
            raise

    async def subscribe(self, channel: dict):
        """Subscribe to ticker updates"""
        await self.ws.send(json.dumps(channel))
        logger.info(f'Subscribed to {channel}')
```

---

## Gap Detection & Recovery

### Identifying Missing Messages

```python
# repositories/postgres.py
class PostgresMarketRepository:
    async def detect_gaps(self, ticker: str) -> list[int]:
        """Detect missing WebSocket sequences"""
        stmt = (
            select(MarketSnapshotModel.sequence)
            .where(
                MarketSnapshotModel.market_ticker == ticker,
                MarketSnapshotModel.source == 'websocket',
                MarketSnapshotModel.sequence.isnot(None)
            )
            .order_by(MarketSnapshotModel.sequence)
        )
        result = await self.session.execute(stmt)
        sequences = [row.sequence for row in result.scalars()]

        # Find gaps
        if not sequences:
            return []

        gaps = []
        for i in range(sequences[0], sequences[-1]):
            if i not in sequences:
                gaps.append(i)

        return gaps
```

### Backfilling from REST

```python
# poller/gap_filler.py
async def backfill_gaps(ticker: str, gaps: list[int]):
    """Use REST API to fill detected gaps"""
    client = KalshiRestClient(api_key=settings.KALSHI_API_KEY)

    for gap_seq in gaps:
        # Estimate timestamp from surrounding sequences
        snapshot = await client.get_market_at_sequence(ticker, gap_seq)

        await repo.save(
            MarketSnapshot(
                market_ticker=ticker,
                yes_price=snapshot['yes_price'],
                source='backfill',  # NEW source type
                sequence=gap_seq,
                timestamp=snapshot['timestamp']
            )
        )
```

**Enhanced DataSource Enum**:
```python
class DataSource(str, enum.Enum):
    REST = 'rest'
    WEBSOCKET = 'websocket'
    BACKFILL = 'backfill'  # NEW: Gap-filled data
```

---

## Frontend Real-Time Updates

### WebSocket Hook (Frontend)

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
    refetchInterval: 1000,  // 1-second polling for "real-time" feel
    // Phase 3: Replace with WebSocket subscription to backend
  });
}
```

**Why Not WebSocket to Frontend Yet?**
- Phase 2 focuses on data collection
- Phase 3 adds WebSocket endpoint in FastAPI for frontend
- Current approach: 1-second polling is sufficient for monitoring

---

## Live Order Book Visualization

### Backend Endpoint

```python
# api/v1/markets.py
@router.get('/{ticker}/orderbook')
async def get_orderbook(
    ticker: str,
    repo: MarketRepository = Depends(get_market_repo)
):
    """Get latest order book snapshot"""
    # In Phase 2, this might be cached from WebSocket messages
    orderbook = await kalshi_client.get_orderbook(ticker)
    return OrderBookResponse.from_kalshi(orderbook)
```

### Frontend Component

```typescript
// components/OrderBookChart.tsx
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis } from 'recharts';

export function OrderBookChart({ ticker }: { ticker: string }) {
  const { data: orderbook } = useQuery({
    queryKey: ['orderbook', ticker],
    queryFn: async () => {
      const response = await apiClient.get(`/api/v1/markets/${ticker}/orderbook`);
      return response.data;
    },
    refetchInterval: 2000,  // 2-second refresh
  });

  const chartData = [
    ...orderbook.yes_bids.map(bid => ({ price: bid[0], volume: bid[1], side: 'bid' })),
    ...orderbook.yes_asks.map(ask => ({ price: ask[0], volume: -ask[1], side: 'ask' })),
  ];

  return (
    <BarChart data={chartData}>
      <XAxis dataKey="price" />
      <YAxis />
      <Bar dataKey="volume" fill={(entry) => entry.side === 'bid' ? '#22c55e' : '#ef4444'} />
    </BarChart>
  );
}
```

---

## Real-Time Strategy Monitoring

### Streaming Strategy Performance

```python
# api/v1/strategies.py
@router.get('/{strategy_name}/performance')
async def get_strategy_performance(
    strategy_name: str,
    repo: StrategyRepository = Depends(get_strategy_repo)
):
    """Get live strategy performance metrics"""
    # Calculate from latest market data
    performance = await strategy_service.calculate_live_performance(strategy_name)

    return StrategyPerformanceResponse(
        total_pnl=performance['pnl'],
        unrealized_pnl=performance['unrealized'],
        sharpe_ratio=performance['sharpe'],
        positions=performance['positions']
    )
```

### Frontend Dashboard

```typescript
// components/StrategyDashboard.tsx
export function StrategyDashboard({ strategyName }: { strategyName: string }) {
  const { data: performance } = useQuery({
    queryKey: ['strategy-performance', strategyName],
    queryFn: async () => {
      const response = await apiClient.get(`/api/v1/strategies/${strategyName}/performance`);
      return response.data;
    },
    refetchInterval: 5000,  // 5-second refresh
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{strategyName} - Live Performance</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <MetricCard label="Total P&L" value={`$${performance.total_pnl}`} />
          <MetricCard label="Unrealized P&L" value={`$${performance.unrealized_pnl}`} />
          <MetricCard label="Sharpe Ratio" value={performance.sharpe_ratio.toFixed(2)} />
          <MetricCard label="Open Positions" value={performance.positions.length} />
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## Updated Database Schema

### No Migration Needed!

Phase 1 models already support Phase 2:

```sql
-- UNCHANGED: Same schema from Phase 1
CREATE TABLE market_snapshots (
    id UUID PRIMARY KEY,
    market_ticker VARCHAR NOT NULL,

    yes_price NUMERIC(10, 4) NOT NULL,
    no_price NUMERIC(10, 4) NOT NULL,
    volume INTEGER NOT NULL,

    source VARCHAR NOT NULL,  -- 'rest', 'websocket', or 'backfill'
    sequence INTEGER,          -- Populated for WebSocket messages
    timestamp TIMESTAMPTZ NOT NULL,

    raw_data JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Phase 2 Usage**:
- REST polling: `source='rest', sequence=NULL`
- WebSocket: `source='websocket', sequence=12345`
- Gap filling: `source='backfill', sequence=12344`

---

## API Changes

### New Endpoints (Phase 2)

```python
# GET /api/v1/markets/{ticker}/latest
# Returns: Latest snapshot (WebSocket if available, else REST)

# GET /api/v1/markets/{ticker}/orderbook
# Returns: Current order book depth

# GET /api/v1/strategies/{name}/performance
# Returns: Live strategy metrics
```

**Backward Compatible**: All Phase 1 endpoints unchanged

---

## Deployment (Docker Compose)

### Updated docker-compose.yml

```yaml
services:
  poller:
    build: ./backend
    command: python -m poller.main  # Runs BOTH REST + WebSocket
    environment:
      - KALSHI_WS_URL=wss://demo-api.kalshi.co/trade-api/ws/v2  # NEW
    # No other changes needed!

  # api and db services unchanged from Phase 1
```

**Key Point**: Poller container seamlessly runs both REST and WebSocket without API changes (ADR-001 benefit)

---

## Testing Strategy

### WebSocket Integration Tests

```python
# tests/test_websocket_poller.py
import pytest
from unittest.mock import AsyncMock

async def test_websocket_saves_to_database():
    mock_ws = AsyncMock()
    mock_ws.__aiter__.return_value = iter([
        {'type': 'ticker', 'ticker': 'TEST', 'yes_price': 52, 'seq': 1},
        {'type': 'ticker', 'ticker': 'TEST', 'yes_price': 53, 'seq': 2},
    ])

    repo = MockRepository()
    await listen_websocket(repo, ws_client=mock_ws)

    assert len(repo.saved_snapshots) == 2
    assert repo.saved_snapshots[0].source == 'websocket'
    assert repo.saved_snapshots[0].sequence == 1
```

### Gap Detection Tests

```python
async def test_gap_detection():
    repo = PostgresMarketRepository(test_db_session)

    # Simulate WebSocket messages with gap
    await repo.save(MarketSnapshot(ticker='TEST', sequence=1, source='websocket'))
    await repo.save(MarketSnapshot(ticker='TEST', sequence=2, source='websocket'))
    await repo.save(MarketSnapshot(ticker='TEST', sequence=4, source='websocket'))  # Gap at 3

    gaps = await repo.detect_gaps('TEST')
    assert gaps == [3]
```

---

## Performance Optimization

### WebSocket Message Throughput

**Expected Load**:
- 100 active markets × 1 update/second = 100 messages/second
- PostgreSQL can handle 1000+ inserts/second
- No bottleneck expected

**If Needed (Phase 3+)**:
- Batch inserts (10-100 messages at a time)
- Redis caching for latest snapshots
- TimescaleDB for time-series optimization

---

## Monitoring & Alerts

### Key Metrics (Phase 2)

```python
# Prometheus metrics (future)
websocket_messages_received = Counter('ws_messages', 'WebSocket messages received')
websocket_gaps_detected = Counter('ws_gaps', 'WebSocket sequence gaps')
websocket_reconnections = Counter('ws_reconnects', 'WebSocket reconnections')
```

### Alerts

- WebSocket disconnected >5 minutes → Alert
- Gap detection rate >1% → Alert
- Poller container crash → Auto-restart + Alert

---

## Phase 2 Success Criteria

### Technical Metrics
- ✅ WebSocket connection uptime >99%
- ✅ Message latency <500ms (Kalshi → Database)
- ✅ Gap detection and backfill working
- ✅ Order book data refreshing every 2 seconds

### Business Metrics
- ✅ Live strategy performance dashboard functional
- ✅ Real-time P&L tracking accurate
- ✅ Faster market data enables better trade timing

---

## Effort Estimate

| Task | Effort | Benefit |
|------|--------|---------|
| Add WebSocket to poller | 1 day | Real-time data |
| Gap detection logic | 0.5 days | Data integrity |
| Frontend live updates | 1 day | Better UX |
| Order book visualization | 0.5 days | Market depth insights |
| Strategy monitoring UI | 1 day | Live performance tracking |
| Testing & debugging | 1 day | Production readiness |
| **Total** | **5 days** | Real-time monitoring platform |

**Why So Fast?**
- ✅ ADR-001: Poller already separate (no API refactor)
- ✅ ADR-002: Repository pattern (no data access changes)
- ✅ ADR-003: Schema ready (no migration)

**Without ADRs**: 2-3 weeks (schema migration + poller extraction + API refactor)

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| WebSocket disconnections | Data gaps | Auto-reconnect + REST backfill |
| Message ordering issues | Incorrect data | Sequence-based gap detection |
| High message volume | Performance degradation | Batch inserts, Redis caching (Phase 3) |
| Kalshi API changes | Breaking changes | Monitor API changelog, version locking |

---

## Next Steps After Phase 2

### Phase 3: Automated Trading (If Phase 2 Validates)

**Additions**:
- Event-driven trade execution (GCP Cloud Tasks or Celery)
- WebSocket endpoint in FastAPI (backend → frontend)
- GCP Cloud Run deployment
- Secret Manager for API keys
- Monitoring and alerting

### Phase 4: Multi-User SaaS (If Demand Exists)

**Additions**:
- User authentication (Firebase Auth)
- GraphQL layer (Strawberry)
- Redis caching
- Horizontal scaling

---

## Summary

**Phase 2 Architecture**: Add WebSocket real-time data to Phase 1 REST foundation

**Key Benefits**:
- ✅ Real-time market monitoring (sub-second updates)
- ✅ Live strategy performance tracking
- ✅ Order book depth visualization
- ✅ No breaking changes to Phase 1 (thanks to ADRs)

**Effort**: 5 days (vs. 2-3 weeks without Phase 1 preparation)

**Decision Gate**: Only build Phase 2 if Phase 1 proves strategy profitability (Sharpe >0.5)

**Architecture Foundation**: The three ADRs from Phase 1 enable this smooth transition with minimal refactoring
