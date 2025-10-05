# Architecture Overview: Kalshi Account Integration

**Audience**: Developers, Technical Stakeholders
**Last Updated**: 2025-10-04
**Status**: Design Phase - SSE Architecture Approved

## Executive Summary

This document provides a high-level architectural overview of the account integration feature for the Kalshi Analysis platform. The system enables real-time position monitoring during market research workflows through authenticated Kalshi API integration with Server-Sent Events (SSE) streaming.

### Quick Facts

- **Architecture Pattern**: Server-Sent Events (SSE) for unidirectional streaming
- **Authentication**: Server-side encrypted credential storage with JWT sessions
- **Real-time Updates**: <1 second latency for position P&L updates
- **Deployment**: Docker Compose (local), Cloud Run-ready (production)
- **Complexity**: Medium-Low (SSE simplification vs. dual WebSocket)

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  KALSHI PRODUCTION API                      │
│         ┌──────────┬──────────────┬─────────────┐          │
│         │  Public  │   Account    │  WebSocket  │          │
│         │   Data   │     Data     │    Feeds    │          │
│         └────┬─────┴──────┬───────┴──────┬──────┘          │
└──────────────┼────────────┼──────────────┼─────────────────┘
               │            │              │
          REST │       REST │ (API key)    │ WebSocket (API key)
               │            │              │
┌──────────────▼────────────▼──────────────▼─────────────────┐
│                  BACKEND (FastAPI)                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Account Service Layer                             │   │
│  │  • AuthenticatedKalshiClient (API calls)           │   │
│  │  • CredentialManager (Fernet encryption)           │   │
│  │  • PositionTracker (P&L calculations)              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Streaming Manager                                  │   │
│  │  • Kalshi WebSocket Client (upstream)              │   │
│  │  • SSE Stream Manager (downstream)                 │   │
│  │  • Queue-based broadcasting                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  PostgreSQL                                         │   │
│  │  • user_credentials (encrypted API keys)           │   │
│  │  • position_cache (write-through cache)            │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────┬──────────────────┬─────────────────────────┘
                 │ REST API         │ SSE Stream
                 │                  │
┌────────────────▼──────────────────▼─────────────────────────┐
│              FRONTEND (React + TypeScript)                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  State Management (Zustand)                        │   │
│  │  • portfolioStore (total value, P&L)               │   │
│  │  • positionsStore (positions array)                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SSE Consumer (EventSource)                        │   │
│  │  • usePositionSSE() hook                           │   │
│  │  • Browser auto-reconnect                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  UI Components                                      │   │
│  │  • PortfolioSummaryBar (top header)                │   │
│  │  • PositionPanel (280px sidebar)                   │   │
│  │  • PositionCard (individual positions)             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Architectural Decisions

### 1. SSE vs WebSocket for Backend→Frontend Communication

**Decision**: Server-Sent Events (SSE)

**Rationale**:
- **Simpler**: ~30% less complexity than dual WebSocket architecture
- **Browser auto-reconnect**: EventSource API handles reconnection automatically
- **Sufficient latency**: <200ms acceptable for read-only position monitoring
- **Easier debugging**: text/event-stream visible in browser DevTools
- **Standard HTTP/2**: No special protocol negotiation required

**Trade-offs**:
- **Unidirectional only**: Cannot send commands from frontend (acceptable for Phase 1 read-only monitoring)
- **Text-based**: Slightly less efficient than binary WebSocket (negligible for our use case)

### 2. Server-Side Encrypted Credential Storage

**Decision**: Fernet symmetric encryption in PostgreSQL

**Rationale**:
- **Security**: API keys never exposed to frontend after initial authentication
- **Simplicity**: Symmetric encryption simpler than asymmetric (single-user deployment)
- **Python-native**: Cryptography library well-maintained and audited
- **Key rotation**: Environment-based secret key allows rotation without code changes

**Implementation**:
```python
# Fernet encryption (AES-128-CBC + HMAC-SHA256)
cipher = Fernet(settings.encryption_secret_key.encode())
encrypted_key = cipher.encrypt(api_key.encode())
```

### 3. Write-Through Position Cache

**Decision**: Database as source of truth, in-memory for performance

**Rationale**:
- **Resilience**: Positions survive backend restarts
- **Reconciliation**: Database enables conflict resolution after disconnects
- **Performance**: In-memory PositionTracker for fast P&L calculations
- **Audit trail**: Historical position data for future analytics

**Pattern**:
```python
# Every position update written to both memory and database
def update_position(ticker, data):
    # Update in-memory state
    state = self.positions[ticker] = PositionState(...)
    # Write-through to database
    db.execute(upsert_position_cache(ticker, state))
    return state
```

### 4. Kalshi WebSocket Upstream

**Decision**: WebSocket for Kalshi→Backend (unchanged)

**Rationale**:
- **Real-time**: Kalshi pushes position/price updates via WebSocket
- **Efficiency**: Avoids polling Kalshi API every second
- **Kalshi native**: Kalshi provides WebSocket API for real-time events

**Events subscribed**:
- `portfolio` - Balance and total value changes
- `positions` - Position quantity/entry price updates
- Market price updates (for positions we hold)

---

## Data Flow Patterns

### 1. Authentication Flow

```
User enters API key
    ↓
POST /api/v1/account/authenticate
    ↓
Backend validates with Kalshi API
    ↓
Backend encrypts and stores in PostgreSQL
    ↓
Backend generates JWT session token (24h)
    ↓
Frontend stores JWT in httpOnly cookie
    ↓
Dashboard enables with position panel
```

### 2. Real-Time Position Update Flow

```
Market price changes on Kalshi
    ↓
Kalshi WebSocket: "market_price_updated" event
    ↓
Backend StreamingManager receives event
    ↓
Backend PositionTracker: update price, recalculate P&L
    ↓
Backend StreamingManager: push to all SSE client queues
    ↓
Backend SSE endpoint: yield event to EventSource clients
    ↓
Frontend usePositionSSE: receive SSE event
    ↓
Frontend positionsStore: update position state
    ↓
UI PositionCard: re-render with new P&L (animated)
```

**Latency Budget**:
- Kalshi → Backend: <100ms
- Backend processing: <50ms
- Backend → Frontend (SSE): <100ms
- Frontend render: <16ms (60fps)
- **Total**: <266ms end-to-end

---

## Component Responsibilities

### Backend Components

#### `AuthenticatedKalshiClient`
- **Purpose**: Authenticated REST API client for Kalshi
- **Responsibilities**: Portfolio/positions/balance fetching, API key validation
- **Key Methods**: `get_portfolio()`, `get_positions()`, `get_balance()`

#### `CredentialManager`
- **Purpose**: Secure credential storage and retrieval
- **Responsibilities**: Fernet encryption/decryption, database persistence
- **Security**: Never returns plain API key to frontend after initial auth

#### `PositionTracker`
- **Purpose**: Position state management and P&L calculation
- **Responsibilities**: Track positions in-memory, calculate unrealized P&L, write-through cache
- **Performance**: <10ms P&L calculation per position

#### `StreamingManager`
- **Purpose**: Dual streaming coordination (Kalshi WebSocket upstream, SSE downstream)
- **Responsibilities**:
  - Connect to Kalshi WebSocket, subscribe to events
  - Manage SSE client queues (one per frontend connection)
  - Route Kalshi events → PositionTracker → SSE clients
  - Handle reconnection with exponential backoff

### Frontend Components

#### `usePositionSSE` Hook
- **Purpose**: EventSource wrapper for position updates
- **Responsibilities**: SSE connection lifecycle, message routing, connection status
- **Browser features**: Automatic reconnection (no manual retry logic needed)

#### `portfolioStore` (Zustand)
- **Purpose**: Portfolio-level state (total value, P&L, balance)
- **Persistence**: localStorage for offline mode

#### `positionsStore` (Zustand)
- **Purpose**: Position array state with CRUD operations
- **Actions**: `setPositions`, `updatePosition`, `removePosition`

#### `PortfolioSummaryBar`
- **Purpose**: Top-level portfolio metrics display
- **Displays**: Total value, today's P&L (color-coded), position count, connection status

#### `PositionPanel`
- **Purpose**: Scrollable sidebar with all open positions
- **Features**: Virtual scrolling (>50 positions), last update timestamp, manual refresh

#### `PositionCard`
- **Purpose**: Individual position display with real-time P&L
- **Features**: Animated updates (Framer Motion), color-coded gains/losses, click to navigate

---

## Security Architecture

### Threat Model & Mitigations

| Threat | Mitigation |
|--------|------------|
| **API key exposure** | Encrypted storage (Fernet), never sent to frontend after auth |
| **Man-in-the-middle** | HTTPS only, TLS for all connections |
| **Unauthorized access** | JWT session tokens (24h expiration), httpOnly cookies |
| **Database breach** | Fernet encryption (AES-128), rotate keys via environment variable |
| **Replay attacks** | JWT expiration, single-user deployment limits attack surface |
| **XSS attacks** | Content Security Policy, input sanitization, httpOnly cookies |

### Encryption Details

**Fernet (API Keys)**:
- Algorithm: AES-128-CBC + HMAC-SHA256
- Key: Environment variable `ENCRYPTION_SECRET_KEY`
- Rotation: Decrypt with old key, re-encrypt with new key

**JWT (Sessions)**:
- Algorithm: HS256 (HMAC-SHA256)
- Payload: `{ user_id, exp }`
- Storage: httpOnly cookie (JavaScript cannot access)
- Expiration: 24 hours, auto-renewal on API requests

---

## Performance Characteristics

### Latency Targets

| Operation | Target | Acceptable | Measurement |
|-----------|--------|------------|-------------|
| Position API fetch | <200ms | <500ms | p50 latency |
| Kalshi WS event → Backend | <100ms | <200ms | Event timestamp diff |
| SSE event → Frontend | <100ms | <200ms | Network tab timing |
| P&L calculation | <10ms | <50ms | Backend profiling |
| UI render | <16ms | <33ms | Chrome DevTools FPS |

### Scalability Considerations

**Single-User (Phase 1)**:
- No horizontal scaling needed
- Single backend instance handles all connections
- In-memory PositionTracker sufficient

**Multi-User (Future)**:
- Redis for shared PositionTracker state across instances
- Cloud Run with auto-scaling
- No sticky sessions needed (SSE is stateless per request)

### Resource Usage

**Backend Memory**: ~50MB baseline + ~1KB per position
- 50 positions: ~50MB
- 500 positions: ~55MB

**Frontend Memory**: ~20MB baseline + ~500B per position
- 50 positions: ~20MB
- 500 positions: ~25MB

**Network Bandwidth**:
- Initial snapshot: ~10KB (50 positions)
- Position update: ~500B per event
- 100 updates/min: ~50KB/min (~3KB/hour)

---

## Deployment Architecture

### Phase 1: Local Development (Current)

**Docker Compose**:
```yaml
services:
  backend:
    environment:
      - ENCRYPTION_SECRET_KEY=${ENCRYPTION_SECRET_KEY}
      - KALSHI_API_BASE=https://trading-api.kalshi.com/trade-api/v2

  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

**Requirements**:
- Python 3.11
- Node.js 22
- PostgreSQL 15+

### Phase 2: Cloud Deployment (Future)

**Google Cloud Run**:
- SSE natively supported (streaming responses)
- No sticky sessions needed (stateless SSE endpoints)
- Shared state via Redis if scaling >1 instance

**Secret Manager**:
```bash
gcloud secrets create encryption-key --data-file=secret.key
```

**Cloud SQL**:
```bash
# Run migrations
alembic upgrade head
```

---

## Error Handling & Resilience

### Connection Failures

**Kalshi WebSocket Disconnect**:
1. Detect disconnection via `ConnectionClosed` exception
2. Exponential backoff: 2s, 4s, 8s, 16s, 32s (max)
3. Max 5 retries before circuit breaker opens
4. Notify SSE clients: `{type: 'connection_status', status: 'reconnecting'}`

**SSE Disconnect**:
1. Browser EventSource auto-reconnects (built-in)
2. Frontend displays "Reconnecting..." status
3. Backend sends new snapshot on reconnect

**Kalshi API Failures**:
1. Rate limiting: Exponential backoff, queue requests
2. Invalid credentials: Clear auth, force re-authentication
3. Maintenance: Display status banner, disable account features

### Data Reconciliation

**On Reconnect**:
1. Fetch full position snapshot via REST
2. Compare with in-memory PositionTracker state
3. Resolve conflicts: Kalshi API is source of truth
4. Update database cache with reconciled state
5. Broadcast full snapshot to SSE clients

**On Startup**:
1. Load positions from database cache
2. Fetch fresh positions from Kalshi API
3. Reconcile differences (Kalshi wins)
4. Initialize PositionTracker with reconciled state

---

## Testing Strategy

### Unit Tests

**Backend**:
- `CredentialManager`: Encryption/decryption roundtrip
- `PositionTracker`: P&L calculations (YES side, NO side, edge cases)
- `StreamingManager`: Queue management, event routing

**Frontend**:
- `usePositionSSE`: EventSource lifecycle, message parsing
- `positionsStore`: State updates, position CRUD operations
- Component rendering: PositionCard, PortfolioSummaryBar

### Integration Tests

**Backend**:
- Full authentication flow: encrypt → store → fetch → decrypt
- Kalshi API client: Real API calls with test credentials
- SSE streaming: Mock events → verify client receives

**Frontend**:
- SSE connection: Connect → receive snapshot → process updates
- State synchronization: SSE event → Zustand update → UI render

### E2E Tests (Playwright)

1. **Full user flow**:
   - Enter API key → Authenticate
   - View positions in sidebar
   - Mock SSE event → Verify P&L update
   - Disconnect SSE → Verify reconnect indicator

2. **Error scenarios**:
   - Invalid credentials → Error message
   - Network offline → Offline banner
   - Position removed → Card disappears

### Load Tests

**Scenario**: 50 positions, 100 price updates/minute
- Backend memory: <100MB
- SSE latency: <200ms p95
- Frontend FPS: >50fps
- No dropped events

---

## Migration Path (3 Weeks)

### Week 1: Backend Foundation
- Database migrations (`user_credentials`, `position_cache`)
- `CredentialManager` + encryption tests
- `AuthenticatedKalshiClient` + Kalshi integration tests
- REST endpoints: `/authenticate`, `/positions`, `/portfolio`, `/logout`

### Week 2: Real-Time Infrastructure
- `PositionTracker` + P&L calculation tests
- `StreamingManager` (Kalshi WebSocket + SSE)
- SSE endpoint: `/sse/positions`
- Load testing: 50 positions, 100 updates/min

### Week 3: Frontend Integration
- Zustand stores (`portfolioStore`, `positionsStore`)
- `usePositionSSE` hook (EventSource)
- UI components (PortfolioSummaryBar, PositionPanel, PositionCard)
- Dashboard layout integration
- E2E tests (Playwright)

---

## Open Questions & Future Work

### Phase 1 Scope

**In Scope**:
- Read-only position monitoring
- Real-time P&L updates
- Single-user local deployment

**Out of Scope**:
- Order placement (quick close buttons)
- Multi-user support
- Position history analytics
- Browser notifications

### Future Enhancements (Phase 4+)

1. **Position Alerts**: Browser notifications for P&L thresholds
2. **Quick Close**: Order placement from position card (1-click exit)
3. **Position History**: PostgreSQL archive for analytics (Sharpe, drawdown)
4. **Multi-User**: User management, multiple Kalshi accounts
5. **Mobile**: Responsive design, mobile-optimized position panel
6. **Strategy Integration**: Compare positions with Phase 1C backtested signals

---

## References

- **Detailed Architecture**: [`docs/architecture-account-integration.md`](./architecture-account-integration.md)
- **Implementation Checklist**: [`docs/implementation-checklist.md`](./implementation-checklist.md)
- **Product Specification**: [`docs/account-dashboard-spec.md`](./account-dashboard-spec.md)
- **Kalshi API Docs**: https://trading-api.readme.io/reference
- **Server-Sent Events Spec**: https://html.spec.whatwg.org/multipage/server-sent-events.html

---

**Document Status**: ✅ Design Approved - Ready for Implementation
**Next Action**: Begin Phase 1 development (database migration + CredentialManager)
