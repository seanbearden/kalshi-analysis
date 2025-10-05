# Implementation Checklist: Account Integration with SSE

**Document Type**: Implementation Roadmap
**Version**: 1.0
**Created**: 2025-10-04
**Architecture**: SSE-based Real-time Position Monitoring

## Overview

This checklist provides a step-by-step implementation guide for adding account integration with Server-Sent Events (SSE) streaming to the Kalshi Analysis platform.

**Key Architectural Decision**: Using SSE (Server-Sent Events) for backend→frontend communication instead of WebSocket for simplicity, browser auto-reconnect, and sufficient latency for read-only position monitoring.

---

## Phase 1: Backend Foundation (Week 1)

### Database Setup

- [ ] **Create Alembic migration for new tables**
  - [ ] `user_credentials` table with encrypted API key storage
  - [ ] `position_cache` table for write-through cache (source of truth)
  - [ ] Add indexes: `user_id` on both tables, `(user_id, ticker)` on position_cache
  - [ ] Run migration: `alembic upgrade head`

- [ ] **Add environment variables**
  - [ ] `ENCRYPTION_SECRET_KEY` - Generate Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
  - [ ] `KALSHI_API_BASE` - Production API URL: `https://trading-api.kalshi.com/trade-api/v2`
  - [ ] `KALSHI_WS_URL` - Production WebSocket: `wss://trading-api.kalshi.com/trade-api/ws/v2`

### Backend Core Services

- [ ] **Implement `CredentialManager`** (`services/account/credential_manager.py`)
  - [ ] `__init__(db: Session)` - Initialize Fernet cipher
  - [ ] `store_credentials(user_id: str, api_key: str)` - Encrypt and upsert
  - [ ] `get_credentials(user_id: str) -> str | None` - Decrypt and return
  - [ ] `delete_credentials(user_id: str)` - Remove credentials
  - [ ] Unit tests: encryption/decryption roundtrip, non-existent user

- [ ] **Implement `AuthenticatedKalshiClient`** (`infrastructure/kalshi/authenticated_client.py`)
  - [ ] Extend existing `KalshiClient` base class
  - [ ] Add `Authorization: Bearer` header in `__init__`
  - [ ] `async get_portfolio() -> Portfolio` - Fetch portfolio snapshot
  - [ ] `async get_positions() -> list[Position]` - Fetch open positions
  - [ ] `async get_balance() -> Balance` - Fetch account balance
  - [ ] Integration tests: Real Kalshi API calls with test credentials

- [ ] **Implement `PositionTracker`** (`services/account/position_tracker.py`)
  - [ ] `PositionState` dataclass with P&L calculation properties
  - [ ] `update_position(ticker, data)` - Update/create position
  - [ ] `update_price(ticker, price)` - Update market price, recalculate P&L
  - [ ] `remove_position(ticker)` - Remove closed position
  - [ ] `get_all_positions()` - Get position list
  - [ ] Unit tests: P&L calculations (YES side, NO side, edge cases)

### REST API Endpoints

- [ ] **Add authentication endpoint** (`/api/v1/account/authenticate`)
  - [ ] POST handler with `api_key` in request body
  - [ ] Validate API key with Kalshi API (test call)
  - [ ] Store encrypted credentials via `CredentialManager`
  - [ ] Generate JWT session token (24h expiration)
  - [ ] Return `{ status, user_id, session_expires_at }`
  - [ ] Error handling: 401 for invalid credentials

- [ ] **Add portfolio endpoint** (`/api/v1/account/portfolio`)
  - [ ] GET handler with JWT authentication
  - [ ] Retrieve credentials via `CredentialManager`
  - [ ] Call `AuthenticatedKalshiClient.get_portfolio()`
  - [ ] Return portfolio snapshot
  - [ ] Error handling: 401 for expired/invalid token

- [ ] **Add positions endpoint** (`/api/v1/account/positions`)
  - [ ] GET handler with JWT authentication
  - [ ] Retrieve credentials, fetch positions from Kalshi
  - [ ] Initialize `PositionTracker` with fetched positions
  - [ ] Return positions array
  - [ ] Error handling: Handle Kalshi API failures gracefully

- [ ] **Add logout endpoint** (`/api/v1/account/logout`)
  - [ ] DELETE handler with JWT authentication
  - [ ] Call `CredentialManager.delete_credentials()`
  - [ ] Invalidate JWT token (add to blocklist if needed)
  - [ ] Return `{ status: "logged_out" }`

### Testing Phase 1

- [ ] **Unit tests**
  - [ ] Credential encryption/decryption
  - [ ] PositionTracker P&L calculations
  - [ ] JWT token generation/validation

- [ ] **Integration tests**
  - [ ] Full authentication flow (store → fetch → decrypt)
  - [ ] Kalshi API client with real credentials
  - [ ] Position fetch and storage

- [ ] **End-to-end test**
  - [ ] POST `/authenticate` → GET `/positions` → GET `/portfolio`
  - [ ] Verify data consistency

---

## Phase 2: Real-time Streaming Infrastructure (Week 2)

### Kalshi WebSocket Client (Upstream)

- [ ] **Extend `StreamingManager`** (`services/account/streaming_manager.py`)
  - [ ] `__init__()` - Initialize with empty queue list, PositionTracker
  - [ ] `async connect_to_kalshi(api_key)` - Establish WebSocket connection
  - [ ] Subscribe to Kalshi channels: `["portfolio", "positions"]`
  - [ ] `async _listen_kalshi()` - Event loop for incoming Kalshi messages
  - [ ] `async _handle_position_update(data)` - Position quantity/entry price change
  - [ ] `async _handle_price_update(data)` - Market price update → recalculate P&L
  - [ ] `async _handle_position_closed(data)` - Remove position from tracker
  - [ ] `async _reconnect()` - Exponential backoff reconnection (2s, 4s, 8s, 16s, 32s max)
  - [ ] Unit tests: Mock Kalshi WebSocket events

### SSE Stream Manager (Downstream)

- [ ] **Add SSE broadcasting to `StreamingManager`**
  - [ ] `update_queues: list[Queue]` - Track all connected SSE clients
  - [ ] `_push_to_sse_clients(message)` - Push to all client queues
  - [ ] `async position_stream() -> AsyncGenerator[str, None]` - SSE event generator
    - [ ] Create client queue on connection
    - [ ] Send initial position snapshot: `data: {type: 'snapshot', positions: [...]}\n\n`
    - [ ] Stream updates from queue: `data: {type: 'position_update', ...}\n\n`
    - [ ] Cleanup queue on client disconnect (finally block)
  - [ ] Unit tests: Queue creation, message broadcasting, cleanup

### SSE API Endpoint

- [ ] **Add SSE endpoint** (`/api/v1/account/sse/positions`)
  - [ ] GET handler with JWT query parameter: `?token=<JWT>`
  - [ ] Authenticate JWT token
  - [ ] Return `StreamingResponse(streaming_manager.position_stream())`
  - [ ] Set headers:
    - [ ] `Content-Type: text/event-stream`
    - [ ] `Cache-Control: no-cache`
    - [ ] `Connection: keep-alive`
  - [ ] Error handling: 401 for invalid token

### Write-Through Position Cache

- [ ] **Add database persistence to `PositionTracker`**
  - [ ] `__init__(db: Session)` - Accept database session
  - [ ] `update_position()` - Write to both memory AND `position_cache` table
  - [ ] `load_from_cache(user_id)` - Restore positions from database on startup
  - [ ] `sync_to_cache()` - Periodic sync to database (every 60s)
  - [ ] Unit tests: Cache read/write, recovery from database

### Testing Phase 2

- [ ] **Mock Kalshi WebSocket events**
  - [ ] Test position_updated event → PositionTracker update
  - [ ] Test market_price_updated → P&L recalculation
  - [ ] Test position_closed → Position removal

- [ ] **SSE flow tests**
  - [ ] Connect SSE client → receive initial snapshot
  - [ ] Push update to queue → verify SSE event delivery
  - [ ] Disconnect SSE client → verify queue cleanup

- [ ] **Reconnection tests**
  - [ ] Kalshi WebSocket disconnect → verify reconnect with backoff
  - [ ] SSE client disconnect → verify EventSource auto-reconnect (browser)

- [ ] **Load test**
  - [ ] 50 positions, 100 price updates/minute
  - [ ] Measure: SSE latency, memory usage, queue depth

---

## Phase 3: Frontend Integration (Week 3)

### Zustand State Management

- [ ] **Create `portfolioStore`** (`features/account/store/portfolioSlice.ts`)
  - [ ] State: `Portfolio | null`
  - [ ] Actions: `setPortfolio(portfolio)`, `updatePnL(todayPnL, todayPnLPercent)`
  - [ ] Persist: localStorage for offline mode

- [ ] **Create `positionsStore`** (`features/account/store/positionsSlice.ts`)
  - [ ] State: `Position[]`, `connectionStatus: 'connected' | 'reconnecting' | 'disconnected'`
  - [ ] Actions:
    - [ ] `setPositions(positions)` - Initial snapshot
    - [ ] `updatePosition(position)` - Update single position
    - [ ] `removePosition(ticker)` - Remove position
    - [ ] `setConnectionStatus(status)` - Update connection state
  - [ ] Persist: localStorage for offline mode

### SSE Hook (EventSource)

- [ ] **Implement `usePositionSSE`** (`features/account/hooks/usePositionSSE.ts`)
  - [ ] `useEffect` to create EventSource on mount
  - [ ] EventSource URL: `/api/v1/account/sse/positions?token=${jwtToken}`
  - [ ] `onmessage` handler:
    - [ ] Parse JSON from `event.data`
    - [ ] Route by message type: snapshot → setPositions, position_update → updatePosition, etc.
  - [ ] `onerror` handler:
    - [ ] Set connection status to 'reconnecting' (browser auto-reconnects)
  - [ ] Cleanup: `eventSource.close()` on unmount
  - [ ] Return: `{ connectionStatus, lastUpdate }`

- [ ] **Implement `usePortfolio`** (`features/account/hooks/usePortfolio.ts`)
  - [ ] Fetch initial portfolio via REST: `GET /api/v1/account/portfolio`
  - [ ] Subscribe to SSE `portfolio_update` events
  - [ ] Update `portfolioStore` on events
  - [ ] Return: `{ portfolio, isLoading, error }`

### UI Components

- [ ] **Create `PortfolioSummaryBar`** (`features/account/components/PortfolioSummaryBar.tsx`)
  - [ ] Display: Total value, Today P&L (color-coded), Position count
  - [ ] Connection status indicator (green/yellow/red dot)
  - [ ] Refresh button (manual portfolio reload)
  - [ ] Skeleton loading state

- [ ] **Create `PositionCard`** (`features/account/components/PositionCard.tsx`)
  - [ ] Display: Ticker, Market title, Side (YES/NO), Quantity, Entry price
  - [ ] P&L: Dollar amount + percentage (color-coded: green/red)
  - [ ] Current price display
  - [ ] Animated P&L updates (Framer Motion)
  - [ ] Click → Navigate to market detail page

- [ ] **Create `PositionPanel`** (`features/account/components/PositionPanel.tsx`)
  - [ ] Fixed 280px width sidebar
  - [ ] Scrollable position list (virtual scrolling if >50 positions)
  - [ ] Empty state: "No open positions"
  - [ ] Last update timestamp
  - [ ] Manual refresh button

- [ ] **Create `AuthDialog`** (`features/account/components/AuthDialog.tsx`)
  - [ ] Input field for Kalshi API key
  - [ ] Submit → POST `/api/v1/account/authenticate`
  - [ ] Store JWT in httpOnly cookie
  - [ ] Error handling: Invalid credentials message
  - [ ] Link to Kalshi API key generation docs

### Dashboard Integration

- [ ] **Update `Layout.tsx`**
  - [ ] Add `PortfolioSummaryBar` at top
  - [ ] Add two-column layout: `<PositionPanel />` (left) + existing content (right)
  - [ ] Responsive: Hide position panel on mobile (<768px)

- [ ] **Update `MarketCard.tsx`**
  - [ ] Check if user owns position for this ticker
  - [ ] Add "You own this market" badge (with P&L indicator)
  - [ ] Highlight card border if position exists

### Testing Phase 3

- [ ] **Component tests (Vitest)**
  - [ ] PositionCard: Renders correctly, P&L calculations display properly
  - [ ] PortfolioSummaryBar: Connection status colors, number formatting
  - [ ] PositionPanel: Virtual scrolling with 100+ positions

- [ ] **E2E tests (Playwright)**
  - [ ] Full authentication flow: Enter API key → See positions
  - [ ] Real-time updates: Mock SSE events → Verify UI updates
  - [ ] Reconnection: Disconnect SSE → Verify reconnect indicator
  - [ ] Market navigation: Click position card → Navigate to market detail

- [ ] **Visual regression tests**
  - [ ] PortfolioSummaryBar: Green P&L, Red P&L, Neutral
  - [ ] PositionCard: Profit state, Loss state
  - [ ] PositionPanel: Empty state, 1 position, 10+ positions

---

## Phase 4: Error Handling & Polish

### Error Scenarios

- [ ] **Kalshi API failures**
  - [ ] Invalid credentials → Clear auth, show re-auth dialog
  - [ ] Rate limiting → Show warning, implement exponential backoff
  - [ ] Kalshi maintenance → Display status message, disable features

- [ ] **Kalshi WebSocket failures**
  - [ ] Connection timeout → Reconnect with exponential backoff
  - [ ] Max retries exceeded → Show error banner, fall back to REST polling
  - [ ] Circuit breaker: Stop reconnecting after 5 consecutive failures

- [ ] **SSE failures**
  - [ ] Browser EventSource error → Display "Reconnecting..." status
  - [ ] JWT expiration during stream → Refresh token, reconnect SSE
  - [ ] Network offline → Detect via `navigator.onLine`, show offline banner

- [ ] **Database failures**
  - [ ] Position cache write failure → Log error, continue with in-memory state
  - [ ] Credential retrieval failure → Force re-authentication

### Reconciliation Strategy

- [ ] **Full snapshot on reconnect**
  - [ ] After Kalshi WebSocket reconnection, fetch full positions via REST
  - [ ] Compare with in-memory state, reconcile differences
  - [ ] Log discrepancies for monitoring

- [ ] **Database reconciliation**
  - [ ] On startup, load positions from `position_cache`
  - [ ] Fetch fresh positions from Kalshi API
  - [ ] Resolve conflicts: Kalshi API is source of truth

### Connection Status System

- [ ] **Rich connection states**
  - [ ] `connected` - Both Kalshi WS and SSE active, green indicator
  - [ ] `kalshi_reconnecting` - Kalshi WS down, yellow indicator
  - [ ] `sse_reconnecting` - SSE disconnected, yellow indicator
  - [ ] `degraded` - Using REST polling fallback, yellow indicator
  - [ ] `disconnected` - Total failure, red indicator, show error message

- [ ] **Status UI component**
  - [ ] Tooltip on hover: Show connection details
  - [ ] Click → Connection diagnostics modal

### Performance Optimization

- [ ] **Backend optimizations**
  - [ ] Use `orjson` for faster JSON serialization
  - [ ] Implement bounded queues (max 1000 events per client)
  - [ ] Add queue overflow handling (drop oldest events)
  - [ ] Connection pooling for PostgreSQL

- [ ] **Frontend optimizations**
  - [ ] React.memo for PositionCard (prevent unnecessary re-renders)
  - [ ] Debounce P&L updates if >10 updates/second
  - [ ] Virtual scrolling for position list (react-window)
  - [ ] Framer Motion: Use `transform` for hardware acceleration

---

## Deployment Checklist

### Local Development

- [ ] **Docker Compose setup**
  - [ ] Add `ENCRYPTION_SECRET_KEY` to `.env` file
  - [ ] Update `KALSHI_API_BASE` to production URL
  - [ ] `docker compose up --build`
  - [ ] Verify SSE endpoint: `curl -N http://localhost:8000/api/v1/account/sse/positions?token=<JWT>`

### CI/CD Pipeline

- [ ] **Backend tests in CI**
  - [ ] Run pytest with coverage
  - [ ] Mock Kalshi API calls
  - [ ] Test database migrations

- [ ] **Frontend tests in CI**
  - [ ] Run Vitest unit tests
  - [ ] Run Playwright E2E tests
  - [ ] Check ESLint, Prettier, TypeScript

### Production Deployment (Future: Cloud Run)

- [ ] **Environment secrets**
  - [ ] Store `ENCRYPTION_SECRET_KEY` in Secret Manager
  - [ ] Configure Cloud Run to inject secret

- [ ] **Database migrations**
  - [ ] Run Alembic migrations on Cloud SQL: `alembic upgrade head`

- [ ] **Monitoring**
  - [ ] SSE connection count metric
  - [ ] Kalshi WebSocket uptime metric
  - [ ] Position cache write latency
  - [ ] Error rate alerts (Kalshi API failures)

---

## Success Criteria

### Functional Requirements

- [x] User can authenticate with Kalshi API key
- [x] Positions displayed in always-visible sidebar (280px)
- [x] Portfolio summary bar shows total value, today's P&L, position count
- [x] Real-time P&L updates within 1 second of market price changes
- [x] SSE connection auto-reconnects on disconnect (browser handles it)
- [x] Graceful degradation to REST polling if SSE fails
- [x] Position cache survives backend restarts

### Performance Requirements

- [x] SSE event latency (backend → frontend): < 200ms
- [x] P&L calculation time: < 50ms
- [x] Frontend UI updates: 60fps (< 16ms per frame)
- [x] Support 50+ open positions without lag

### Security Requirements

- [x] API keys encrypted with Fernet (AES-128)
- [x] Never expose plain API key to frontend after auth
- [x] JWT session tokens with 24h expiration
- [x] HTTPS/TLS for all communication
- [x] Environment variables for secrets (no hardcoded keys)

### Reliability Requirements

- [x] 99.5% WebSocket uptime (Kalshi → Backend)
- [x] Automatic reconnection within 5 seconds (exponential backoff)
- [x] Browser auto-reconnect for SSE (EventSource built-in)
- [x] Write-through position cache as source of truth

---

## Notes and Recommendations

### From System Architect Review

1. **SSE is sufficient for Phase 1** - Unidirectional streaming is all we need for read-only monitoring
2. **Position cache is NOT optional** - Write-through cache is the source of truth for resilience
3. **Circuit breaker for Kalshi API** - Prevent cascading failures from upstream API issues
4. **Rich connection status** - Beyond binary connected/disconnected for better UX

### Future Enhancements (Phase 4+)

- [ ] Position alerts (P&L thresholds trigger browser notifications)
- [ ] Quick close buttons (order placement from position card)
- [ ] Position history tracking (PostgreSQL archive for analytics)
- [ ] Multi-user support (multiple Kalshi accounts, user management)
- [ ] Portfolio performance analytics (Sharpe ratio, drawdown, win rate)

---

**Status**: Ready for Phase 1 implementation
**Next Step**: Begin with database migration and `CredentialManager` implementation
