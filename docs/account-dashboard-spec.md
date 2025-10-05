# Account Dashboard Specification

**Feature**: Real-time Position Monitoring During Market Research
**Version**: 1.0
**Created**: 2025-10-04
**Status**: Specification Phase

## Executive Summary

Enhance the Kalshi Analysis dashboard with real-time position monitoring, enabling users to maintain ambient awareness of their portfolio while researching new market opportunities. Uses authenticated Kalshi API with WebSocket subscriptions for live updates.

## Core Use Case

**Primary Workflow**: User browses and analyzes multiple markets while monitoring open positions without context-switching.

**Success Criteria**:
- Portfolio status visible at all times during market research
- Position updates arrive within 1 second of market changes
- No interruption to market research workflow
- One-glance portfolio health assessment

## Layout Design: Option B - Always-Visible Position Panel

```
┌─────────────────────────────────────────────────────────────┐
│  Portfolio Summary Bar (always visible)                     │
│  💰 $10,245.32 | Today: +$127.50 (+1.26%) | 5 positions    │
└─────────────────────────────────────────────────────────────┘
┌──────────────────┬──────────────────────────────────────────┐
│ Positions Panel  │  Market Research (main content)          │
│ (280px wide)     │                                          │
│                  │                                          │
│ ┌──────────────┐ │  Current functionality:                  │
│ │ INXD-25JAN01 │ │  - Market cards with order books        │
│ │ YES: 100 @ 68│ │  - Trade tape                            │
│ │ P&L: +$3.00  │ │  - Implied probabilities                │
│ │ ────────────│ │  - Price charts                          │
│ │ 🟢 +4.4%     │ │                                          │
│ └──────────────┘ │  Enhanced:                               │
│                  │  - "You own this market" badge           │
│ ┌──────────────┐ │  - Position-aware highlighting          │
│ │ KXUSD-25H    │ │                                          │
│ │ NO: 50 @ 42  │ │                                          │
│ │ P&L: -$1.20  │ │                                          │
│ │ ────────────│ │                                          │
│ │ 🔴 -2.3%     │ │                                          │
│ └──────────────┘ │                                          │
│                  │                                          │
│ [+ 3 more...]    │                                          │
│                  │                                          │
│ [Refresh]        │                                          │
│ Last: 2s ago     │                                          │
└──────────────────┴──────────────────────────────────────────┘
```

### Component Hierarchy

**Top Level:**
1. **Portfolio Summary Bar** - Persistent header
2. **Two-column layout**:
   - Left: Position Panel (fixed 280px, scrollable)
   - Right: Market Research (flexible width)

## Technical Architecture

### Frontend Components

**New Components:**
```
frontend/src/features/account/
├── components/
│   ├── PortfolioSummaryBar.tsx      # Top-level portfolio metrics
│   ├── PositionPanel.tsx             # Left sidebar container
│   ├── PositionCard.tsx              # Individual position display
│   ├── PositionDetails.tsx           # Expanded position view
│   └── AccountConnectionStatus.tsx   # WebSocket connection indicator
├── hooks/
│   ├── usePortfolio.ts               # Portfolio data hook
│   ├── usePositions.ts               # Positions list hook
│   ├── usePositionWebSocket.ts       # Real-time updates
│   └── useAccountAuth.ts             # API credential management
├── store/
│   ├── portfolioSlice.ts             # Portfolio state (Zustand)
│   └── positionsSlice.ts             # Positions state (Zustand)
└── types/
    └── account.ts                     # TypeScript types
```

**Modified Components:**
```
frontend/src/components/
├── Layout.tsx                         # Add position panel slot
└── MarketCard.tsx                     # Add position badge if user owns market
```

### Backend Architecture

**New Backend Services:**
```
backend/services/account/
├── kalshi_account_client.py           # Authenticated Kalshi API client
├── portfolio_service.py               # Portfolio data aggregation
├── position_tracker.py                # Position state management
└── websocket_manager.py               # WebSocket connection management
```

**API Endpoints:**
```
POST   /api/account/authenticate        # Store encrypted API credentials
GET    /api/account/portfolio           # Get current portfolio snapshot
GET    /api/account/positions           # Get all open positions
GET    /api/account/balance             # Get account balance
WS     /api/account/ws/positions        # WebSocket for real-time position updates
DELETE /api/account/logout              # Clear stored credentials
```

### Data Flow

**Initial Load:**
1. User authenticates with Kalshi API key (stored encrypted in backend)
2. Backend fetches initial portfolio/positions via REST
3. Frontend displays initial state
4. WebSocket connection established for real-time updates

**Real-time Updates:**
1. Backend subscribes to Kalshi position/portfolio WebSocket events
2. On market price change → Backend recalculates position P&L
3. Backend pushes update to frontend WebSocket
4. Frontend updates position card with new P&L (animated)

**Error Handling:**
- WebSocket disconnection → Show "Reconnecting..." indicator
- API auth failure → Prompt for re-authentication
- Position fetch error → Show cached data + warning banner

## Data Models

### Frontend Types

```typescript
interface Portfolio {
  totalValue: number;           // Current portfolio value
  cashBalance: number;          // Available cash
  todayPnL: number;            // Today's P&L in dollars
  todayPnLPercent: number;     // Today's P&L percentage
  totalPnL: number;            // All-time P&L
  positionCount: number;        // Number of open positions
  lastUpdated: Date;            // Last update timestamp
}

interface Position {
  id: string;                   // Unique position ID
  ticker: string;               // Market ticker
  marketTitle: string;          // Human-readable market name
  side: 'YES' | 'NO';          // Position side
  quantity: number;             // Number of contracts
  avgEntryPrice: number;        // Average entry price (cents)
  currentPrice: number;         // Current market price (cents)
  unrealizedPnL: number;        // Current P&L (dollars)
  unrealizedPnLPercent: number; // Current P&L percentage
  durationHeld: number;         // Time held (seconds)
  expirationDate: Date | null;  // Market expiration/resolution
  lastUpdated: Date;            // Last price update
}

interface PositionUpdate {
  ticker: string;
  currentPrice: number;
  timestamp: Date;
}
```

### Backend Models

```python
from pydantic import BaseModel

class KalshiCredentials(BaseModel):
    email: str
    api_key: str
    # Stored encrypted in database

class PortfolioSnapshot(BaseModel):
    total_value: float
    cash_balance: float
    today_pnl: float
    total_pnl: float
    position_count: int
    timestamp: datetime

class Position(BaseModel):
    ticker: str
    market_title: str
    side: Literal['YES', 'NO']
    quantity: int
    avg_entry_price: int  # cents
    current_price: int    # cents
    unrealized_pnl: float
    duration_held: timedelta
    expiration_date: datetime | None
```

## WebSocket Integration

### Kalshi WebSocket Events (Subscriptions)

**To Subscribe:**
```json
{
  "type": "subscribe",
  "channels": [
    "portfolio",           // Portfolio-level updates
    "positions",          // Position changes (fills, closes)
    "orderbook:TICKER"    // Price updates for markets with positions
  ]
}
```

**Events Received:**
- `position_updated` - Position quantity/entry price changed
- `market_price_updated` - Market price changed (affects P&L)
- `portfolio_updated` - Balance/total value changed
- `position_closed` - Position fully exited

### Custom Backend → Frontend WebSocket

**Message Types:**
```typescript
type WSMessage =
  | { type: 'portfolio_update', data: Portfolio }
  | { type: 'position_update', data: Position }
  | { type: 'position_removed', ticker: string }
  | { type: 'connection_status', status: 'connected' | 'disconnected' | 'reconnecting' }
  | { type: 'error', message: string };
```

## Security & Authentication

**API Credential Storage:**
- User enters Kalshi API key in frontend settings
- Backend encrypts key with Fernet (symmetric encryption)
- Stores encrypted key in PostgreSQL `user_credentials` table
- Never sends plain API key to frontend after initial auth

**Session Management:**
- JWT token for backend API authentication
- Token includes user_id for credential lookup
- WebSocket connection authenticated via token in initial handshake

**Environment Variables:**
```bash
# .env
ENCRYPTION_SECRET_KEY=<fernet-key>      # For API key encryption
KALSHI_API_BASE=https://api.kalshi.com  # Kalshi API base URL
KALSHI_WS_URL=wss://api.kalshi.com/ws   # Kalshi WebSocket URL
```

## Implementation Phases

### Phase 1: Foundation (Week 1)
**Backend:**
- [ ] Kalshi authenticated API client
- [ ] Encrypted credential storage
- [ ] Portfolio REST endpoints
- [ ] Position REST endpoints

**Frontend:**
- [ ] Authentication flow (API key input)
- [ ] Portfolio summary bar component
- [ ] Basic position list (static data)

**Deliverable**: User can authenticate and see snapshot of positions

### Phase 2: Real-time Updates (Week 2)
**Backend:**
- [ ] WebSocket manager for Kalshi connection
- [ ] Position P&L calculation engine
- [ ] Backend → Frontend WebSocket server

**Frontend:**
- [ ] WebSocket hook implementation
- [ ] Real-time position updates
- [ ] Connection status indicators
- [ ] Animated P&L changes

**Deliverable**: Positions update in real-time as market prices change

### Phase 3: Polish & Integration (Week 3)
**Frontend:**
- [ ] Position panel UI refinement
- [ ] "You own this market" badges on market cards
- [ ] Position detail modal/expansion
- [ ] Error handling and retry logic

**Backend:**
- [ ] Reconnection logic for Kalshi WS
- [ ] Caching layer for offline mode
- [ ] Performance optimization

**Deliverable**: Production-ready position monitoring

### Phase 4: Advanced Features (Future)
- [ ] Position alerts (P&L thresholds)
- [ ] Quick order placement from position card
- [ ] Strategy signal comparison (Phase 1C integration)
- [ ] Portfolio performance analytics (Sharpe, drawdown)

## Integration with Phase 1C

**Future Enhancement**: Compare live positions with backtested strategy signals

Example position card enhancement:
```
┌──────────────────┐
│ INXD-25JAN01     │
│ YES: 100 @ 68¢   │
│ P&L: +$3.00      │
│ ────────────────│
│ 🟢 +4.4%         │
│                  │
│ 📊 Strategy:     │
│ ✅ HOLD (match)  │  ← From Phase 1C mean reversion
│ Entry: Good      │
└──────────────────┘
```

## Success Metrics

**User Experience:**
- Position updates visible within 1 second of market change
- Portfolio summary never more than 5 seconds stale
- Zero UI blocking during position updates

**Performance:**
- WebSocket latency < 200ms (backend ↔ Kalshi)
- Frontend rendering < 16ms (60fps)
- Support 50+ open positions without lag

**Reliability:**
- 99.5% WebSocket uptime
- Automatic reconnection within 5 seconds
- Graceful degradation to polling if WS unavailable

## Open Questions

1. **Position History**: Should we store historical positions in PostgreSQL for later analysis?
2. **Multi-User**: Single user (you) or support for multiple Kalshi accounts?
3. **Mobile**: Desktop-first, or also mobile-responsive?
4. **Notifications**: Browser notifications for significant P&L changes?

## Next Steps

1. **Review this spec** - Confirm alignment with vision
2. **API exploration** - Test Kalshi WebSocket API with your credentials
3. **Create PRD** - Expand into full Product Requirements Document
4. **Begin Phase 1** - Start with backend authentication foundation

---

**Questions?** Let me know if anything needs adjustment before we move to implementation!
