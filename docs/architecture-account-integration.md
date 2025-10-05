# System Architecture: Account Integration

**Document Type**: Technical Architecture Design
**Version**: 1.0
**Created**: 2025-10-04
**Feature**: Real-time Position Monitoring Dashboard

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [Current System Architecture](#current-system-architecture)
3. [Proposed Architecture](#proposed-architecture)
4. [Component Design](#component-design)
5. [Data Flow](#data-flow)
6. [Security Architecture](#security-architecture)
7. [SSE Architecture](#sse-architecture)
8. [Database Schema](#database-schema)
9. [API Specification](#api-specification)
10. [Deployment Architecture](#deployment-architecture)
11. [Performance Considerations](#performance-considerations)
12. [Migration Strategy](#migration-strategy)

---

## Executive Summary

### Business Context
Extend the Kalshi Analysis platform to integrate authenticated user account data, enabling real-time position monitoring during market research workflows.

### Technical Approach
- **Backend**: Add authenticated Kalshi API client + SSE streaming + encrypted credential storage
- **Frontend**: Add position panel UI + EventSource consumer + state management
- **Infrastructure**: Minimal changes - reuse existing PostgreSQL, add encryption layer
- **Complexity**: Medium-Low - introduces authentication, encryption, and unidirectional streaming (SSE)

### Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Authentication** | Server-side encrypted storage | User credentials never exposed to frontend |
| **Real-time updates** | Server-Sent Events (SSE) | Simpler than WebSocket, browser auto-reconnect, sufficient for read-only |
| **Upstream data** | Kalshi WebSocket | Real-time position/price events from Kalshi |
| **State management** | Zustand (frontend) | Lightweight, TypeScript-first, good DX |
| **Encryption** | Fernet (symmetric) | Simple, secure, Python-native |
| **Position storage** | Write-through cache (DB + memory) | Survives restarts, enables audit trail |
| **Position calculation** | Backend-side | Centralized logic, reduces frontend complexity |

---

## Current System Architecture

### Phase 1 Architecture (Existing)

```
┌─────────────────────────────────────────────────────────────┐
│                    KALSHI DEMO API                          │
│               (Unauthenticated, Public Data)                │
└────────────────┬────────────────────────────────────────────┘
                 │ REST (polling every 5s)
                 │
┌────────────────▼────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Kalshi Client (infrastructure/kalshi/)              │  │
│  │  - REST client for markets, events, order books      │  │
│  │  - No authentication required                        │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Domain Services (domain/)                           │  │
│  │  - Market service                                    │  │
│  │  - Backtest service                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  API Routes (api/v1/)                                │  │
│  │  - GET /markets                                      │  │
│  │  - GET /markets/{ticker}/orderbook                   │  │
│  │  - GET /backtests                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  PostgreSQL (via SQLAlchemy)                         │  │
│  │  - market_snapshots                                  │  │
│  │  - backtest_results                                  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────────────────┘
                 │ REST API
                 │
┌────────────────▼────────────────────────────────────────────┐
│                FRONTEND (React + TypeScript)                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  TanStack Query (API state management)               │  │
│  │  - useMarkets(), useOrderbook()                      │  │
│  │  - 5s polling intervals                              │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Components                                          │  │
│  │  - MarketCard, OrderbookView, BacktestResults       │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  UI Library: shadcn/ui + Recharts                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Characteristics
- **Single-user, local deployment** (Docker Compose)
- **Unauthenticated data** (demo API, public markets only)
- **REST-only** (no WebSockets yet)
- **PostgreSQL** stores historical snapshots for backtesting
- **No user state** (stateless API)

---

## Proposed Architecture

### Enhanced Architecture (Account Integration)

```
┌─────────────────────────────────────────────────────────────┐
│                  KALSHI PRODUCTION API                      │
│            (Authenticated, User-Specific Data)              │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │ Public Data  │  │ Account Data │  │ WebSocket Feeds │  │
│  │ (markets,    │  │ (portfolio,  │  │ (real-time      │  │
│  │  orderbooks) │  │  positions)  │  │  updates)       │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │
└─────────┼──────────────────┼──────────────────┼────────────┘
          │                  │                  │
          │ REST             │ REST             │ WebSocket
          │ (unauthenticated)│ (API key)        │ (API key)
          │                  │                  │
┌─────────▼──────────────────▼──────────────────▼────────────┐
│                  BACKEND (FastAPI)                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  NEW: Account Service Layer                        │   │
│  │  ┌───────────────────────────────────────────────┐ │   │
│  │  │ Authenticated Kalshi Client                   │ │   │
│  │  │ - Uses stored user credentials                │ │   │
│  │  │ - Portfolio/positions REST endpoints          │ │   │
│  │  └───────────────────────────────────────────────┘ │   │
│  │  ┌───────────────────────────────────────────────┐ │   │
│  │  │ Position Tracker                              │ │   │
│  │  │ - Manages position state                      │ │   │
│  │  │ - Calculates P&L on price updates             │ │   │
│  │  │ - Emits position updates                      │ │   │
│  │  └───────────────────────────────────────────────┘ │   │
│  │  ┌───────────────────────────────────────────────┐ │   │
│  │  │ Credential Manager                            │ │   │
│  │  │ - Fernet encryption/decryption                │ │   │
│  │  │ - Secure storage in PostgreSQL                │ │   │
│  │  └───────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  NEW: Streaming Manager                           │   │
│  │  ┌───────────────────────────────────────────────┐ │   │
│  │  │ Kalshi WebSocket Client (upstream)            │ │   │
│  │  │ - Subscribes to portfolio/position events     │ │   │
│  │  │ - Subscribes to orderbook updates (positions) │ │   │
│  │  │ - Handles reconnection logic                  │ │   │
│  │  │ - Feeds PositionTracker with updates          │ │   │
│  │  └───────────────────────────────────────────────┘ │   │
│  │  ┌───────────────────────────────────────────────┐ │   │
│  │  │ SSE Stream Manager (downstream)               │ │   │
│  │  │ - Manages EventSource connections             │ │   │
│  │  │ - Streams position updates to frontend        │ │   │
│  │  │ - Connection authentication (JWT)             │ │   │
│  │  │ - Browser handles auto-reconnect              │ │   │
│  │  └───────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  EXISTING: Market Service (unchanged)              │   │
│  │  - Public market data via demo API                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  NEW: API Routes (api/v1/account/)                 │   │
│  │  - POST   /account/authenticate                    │   │
│  │  - GET    /account/portfolio                       │   │
│  │  - GET    /account/positions                       │   │
│  │  - DELETE /account/logout                          │   │
│  │  - SSE    /account/sse/positions                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  PostgreSQL (via SQLAlchemy)                       │   │
│  │  EXISTING TABLES:                                  │   │
│  │  - market_snapshots                                │   │
│  │  - backtest_results                                │   │
│  │  NEW TABLES:                                       │   │
│  │  - user_credentials (encrypted API keys)           │   │
│  │  - position_cache (for offline mode)               │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────┬──────────────────┬─────────────────────────┘
                 │ REST API         │ WebSocket
                 │                  │
┌────────────────▼──────────────────▼─────────────────────────┐
│              FRONTEND (React + TypeScript)                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  NEW: Account State (Zustand)                      │   │
│  │  - portfolioStore (total value, P&L, balance)      │   │
│  │  - positionsStore (array of positions)             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  NEW: SSE Hooks (EventSource)                      │   │
│  │  - usePositionSSE()                                │   │
│  │  - usePortfolio()                                  │   │
│  │  - Browser auto-reconnect, error states            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  NEW: Account Components                           │   │
│  │  - PortfolioSummaryBar (top header)                │   │
│  │  - PositionPanel (left sidebar)                    │   │
│  │  - PositionCard (individual positions)             │   │
│  │  - AuthDialog (API key input)                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  EXISTING: Market Components (enhanced)            │   │
│  │  - MarketCard (add "You own this" badge)           │   │
│  │  - Dashboard (add position panel slot)             │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Architectural Changes Summary

| Layer | Changes | Rationale |
|-------|---------|-----------|
| **Kalshi API** | Switch to production API with authentication | Required for account data access |
| **Backend Services** | Add account service layer (3 new modules) | Encapsulate auth, credentials, position logic |
| **Backend Streaming** | Add Kalshi WebSocket client + SSE manager | Enable real-time updates Kalshi → Backend → Frontend |
| **Database** | Add 2 new tables (credentials, cache) | Persist encrypted keys + write-through cache |
| **Backend API** | Add 4 REST + 1 SSE endpoint | Account data access + real-time stream |
| **Frontend State** | Add Zustand stores (portfolio, positions) | Centralized account state management |
| **Frontend Components** | Add account UI (4 new components) | Position monitoring interface |
| **Frontend Hooks** | Add EventSource hooks | SSE stream consumption |

---

## Component Design

### Backend Components

#### 1. **Authenticated Kalshi Client** (`infrastructure/kalshi/authenticated_client.py`)

**Purpose**: Extend existing Kalshi client with authentication support

```python
from infrastructure.kalshi.base_client import KalshiClient

class AuthenticatedKalshiClient(KalshiClient):
    """Kalshi API client with authentication support."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://trading-api.kalshi.com/trade-api/v2",
    ):
        super().__init__(base_url=base_url)
        self.api_key = api_key
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    async def get_portfolio(self) -> Portfolio:
        """Get user portfolio snapshot."""
        response = await self.session.get("/portfolio")
        return Portfolio(**response.json())

    async def get_positions(self) -> list[Position]:
        """Get all open positions."""
        response = await self.session.get("/portfolio/positions")
        return [Position(**p) for p in response.json()["positions"]]

    async def get_balance(self) -> Balance:
        """Get account balance."""
        response = await self.session.get("/portfolio/balance")
        return Balance(**response.json())
```

**Dependencies**:
- Reuses existing `KalshiClient` base class
- Adds `Authorization` header to all requests
- Pydantic models for typed responses

---

#### 2. **Credential Manager** (`services/account/credential_manager.py`)

**Purpose**: Secure storage and retrieval of user API keys

```python
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from core.config import get_settings

class CredentialManager:
    """Manage encrypted user API credentials."""

    def __init__(self, db: Session):
        self.db = db
        settings = get_settings()
        self.cipher = Fernet(settings.encryption_secret_key.encode())

    def store_credentials(self, user_id: str, api_key: str) -> None:
        """Encrypt and store user API key."""
        encrypted_key = self.cipher.encrypt(api_key.encode()).decode()

        # Upsert to database
        credential = self.db.query(UserCredential).filter_by(user_id=user_id).first()
        if credential:
            credential.encrypted_api_key = encrypted_key
        else:
            credential = UserCredential(
                user_id=user_id,
                encrypted_api_key=encrypted_key
            )
            self.db.add(credential)

        self.db.commit()

    def get_credentials(self, user_id: str) -> str | None:
        """Decrypt and return user API key."""
        credential = self.db.query(UserCredential).filter_by(user_id=user_id).first()
        if not credential:
            return None

        decrypted_key = self.cipher.decrypt(credential.encrypted_api_key.encode()).decode()
        return decrypted_key

    def delete_credentials(self, user_id: str) -> None:
        """Remove user API key."""
        self.db.query(UserCredential).filter_by(user_id=user_id).delete()
        self.db.commit()
```

**Security Features**:
- **Fernet encryption** (AES-128, HMAC for authentication)
- **Secret key from environment** (never hardcoded)
- **Database-only storage** (not in memory after use)
- **User isolation** (credentials tied to user_id)

---

#### 3. **Position Tracker** (`services/account/position_tracker.py`)

**Purpose**: Maintain position state and calculate real-time P&L

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PositionState:
    ticker: str
    side: Literal['YES', 'NO']
    quantity: int
    avg_entry_price: int  # cents
    current_price: int    # cents
    entry_time: datetime

    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized P&L in dollars."""
        if self.side == 'YES':
            return (self.current_price - self.avg_entry_price) * self.quantity / 100
        else:  # NO side
            return (self.avg_entry_price - self.current_price) * self.quantity / 100

    @property
    def unrealized_pnl_percent(self) -> float:
        """Calculate unrealized P&L as percentage."""
        if self.avg_entry_price == 0:
            return 0.0
        return (self.unrealized_pnl / (self.avg_entry_price * self.quantity / 100)) * 100


class PositionTracker:
    """Track and calculate position P&L."""

    def __init__(self):
        self.positions: dict[str, PositionState] = {}

    def update_position(self, ticker: str, position_data: dict) -> PositionState:
        """Update or create position from API data."""
        state = PositionState(
            ticker=ticker,
            side=position_data["side"],
            quantity=position_data["quantity"],
            avg_entry_price=position_data["avg_entry_price"],
            current_price=position_data.get("current_price", position_data["avg_entry_price"]),
            entry_time=position_data["entry_time"],
        )
        self.positions[ticker] = state
        return state

    def update_price(self, ticker: str, new_price: int) -> PositionState | None:
        """Update position with new market price, recalculate P&L."""
        if ticker not in self.positions:
            return None

        self.positions[ticker].current_price = new_price
        return self.positions[ticker]

    def remove_position(self, ticker: str) -> None:
        """Remove closed position."""
        self.positions.pop(ticker, None)

    def get_all_positions(self) -> list[PositionState]:
        """Get all tracked positions."""
        return list(self.positions.values())
```

**Design Rationale**:
- **In-memory state** for fast P&L calculations
- **Immutable dataclass** for position snapshots
- **Property methods** for derived values (P&L, percentages)
- **Simple dict storage** (keyed by ticker)

---

#### 4. **Streaming Manager** (`services/account/streaming_manager.py`)

**Purpose**: Manage Kalshi WebSocket (upstream) and SSE streams (downstream to frontend)

```python
import asyncio
import websockets
import json
from typing import AsyncGenerator
from queue import Queue

class StreamingManager:
    """Manage Kalshi WebSocket subscription and SSE broadcasting."""

    def __init__(self):
        self.kalshi_ws: websockets.WebSocketClientProtocol | None = None
        self.position_tracker = PositionTracker()
        self.is_connected = False
        self.update_queues: list[Queue] = []  # SSE client queues

    async def connect_to_kalshi(self, api_key: str):
        """Establish WebSocket connection to Kalshi."""
        uri = f"wss://trading-api.kalshi.com/trade-api/ws/v2"
        headers = {"Authorization": f"Bearer {api_key}"}

        self.kalshi_ws = await websockets.connect(uri, extra_headers=headers)
        self.is_connected = True

        # Subscribe to position updates
        await self.kalshi_ws.send(json.dumps({
            "type": "subscribe",
            "channels": ["portfolio", "positions"]
        }))

        # Start listening loop
        asyncio.create_task(self._listen_kalshi())

    async def _listen_kalshi(self):
        """Listen for Kalshi WebSocket events."""
        try:
            async for message in self.kalshi_ws:
                data = json.loads(message)

                if data["type"] == "position_updated":
                    await self._handle_position_update(data)
                elif data["type"] == "market_price_updated":
                    await self._handle_price_update(data)
                elif data["type"] == "position_closed":
                    await self._handle_position_closed(data)

        except websockets.exceptions.ConnectionClosed:
            self.is_connected = False
            await self._reconnect()

    async def _handle_position_update(self, data: dict):
        """Handle position quantity/entry price change."""
        position = self.position_tracker.update_position(
            ticker=data["ticker"],
            position_data=data["position"]
        )
        self._push_to_sse_clients({
            "type": "position_update",
            "data": position.__dict__
        })

    async def _handle_price_update(self, data: dict):
        """Handle market price change (recalculate P&L)."""
        position = self.position_tracker.update_price(
            ticker=data["ticker"],
            new_price=data["price"]
        )
        if position:
            self._push_to_sse_clients({
                "type": "position_update",
                "data": position.__dict__
            })

    async def _handle_position_closed(self, data: dict):
        """Handle position close event."""
        self.position_tracker.remove_position(data["ticker"])
        self._push_to_sse_clients({
            "type": "position_removed",
            "ticker": data["ticker"]
        })

    def _push_to_sse_clients(self, message: dict):
        """Push message to all SSE client queues."""
        for queue in self.update_queues:
            queue.put_nowait(message)

    async def position_stream(self) -> AsyncGenerator[str, None]:
        """SSE event generator for position updates."""
        # Create queue for this client
        client_queue = Queue()
        self.update_queues.append(client_queue)

        try:
            # Send initial snapshot
            positions = self.position_tracker.get_all_positions()
            yield f"data: {json.dumps({'type': 'snapshot', 'positions': [p.__dict__ for p in positions]})}\n\n"

            # Stream updates
            while True:
                update = await asyncio.get_event_loop().run_in_executor(
                    None, client_queue.get
                )
                yield f"data: {json.dumps(update)}\n\n"

        finally:
            # Cleanup on disconnect
            self.update_queues.remove(client_queue)

    async def _reconnect(self):
        """Attempt to reconnect to Kalshi WebSocket."""
        retries = 0
        max_retries = 5

        while retries < max_retries:
            await asyncio.sleep(2 ** retries)  # Exponential backoff
            try:
                await self.connect_to_kalshi(self.api_key)
                break
            except Exception:
                retries += 1

        if not self.is_connected:
            # Push connection failure to SSE clients
            self._push_to_sse_clients({
                "type": "connection_status",
                "status": "disconnected"
            })
```

**Key Features**:
- **Kalshi WebSocket client** (upstream, subscribes to position/portfolio events)
- **SSE stream generator** (downstream, yields Server-Sent Events to frontend)
- **Queue-based broadcasting** (each SSE client gets dedicated queue)
- **Automatic cleanup** (remove queue on client disconnect)
- **Initial snapshot** (send current positions when SSE stream starts)
- **Reconnection logic** (exponential backoff for Kalshi connection)

---

### Frontend Components

#### 1. **Portfolio Summary Bar** (`features/account/components/PortfolioSummaryBar.tsx`)

```typescript
interface PortfolioSummaryBarProps {}

export function PortfolioSummaryBar() {
  const portfolio = usePortfolio();

  if (!portfolio) {
    return <Skeleton className="h-14 w-full" />;
  }

  const pnlColor = portfolio.todayPnL >= 0 ? 'text-green-600' : 'text-red-600';

  return (
    <div className="border-b bg-card px-6 py-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div>
            <p className="text-sm text-muted-foreground">Portfolio Value</p>
            <p className="text-2xl font-bold">
              ${portfolio.totalValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </p>
          </div>

          <Separator orientation="vertical" className="h-10" />

          <div>
            <p className="text-sm text-muted-foreground">Today</p>
            <p className={`text-lg font-semibold ${pnlColor}`}>
              {portfolio.todayPnL >= 0 ? '+' : ''}
              ${portfolio.todayPnL.toFixed(2)}
              {' '}
              ({portfolio.todayPnLPercent >= 0 ? '+' : ''}
              {portfolio.todayPnLPercent.toFixed(2)}%)
            </p>
          </div>

          <Separator orientation="vertical" className="h-10" />

          <div>
            <p className="text-sm text-muted-foreground">Positions</p>
            <p className="text-lg font-semibold">{portfolio.positionCount}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <ConnectionStatus />
          <Button variant="ghost" size="sm">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
```

---

#### 2. **Position Card** (`features/account/components/PositionCard.tsx`)

```typescript
interface PositionCardProps {
  position: Position;
}

export function PositionCard({ position }: PositionCardProps) {
  const pnlColor = position.unrealizedPnL >= 0 ? 'text-green-600' : 'text-red-600';
  const pnlIcon = position.unrealizedPnL >= 0 ? '🟢' : '🔴';

  return (
    <Card className="overflow-hidden">
      <CardContent className="p-4">
        <div className="mb-2">
          <p className="font-mono text-sm text-muted-foreground">{position.ticker}</p>
          <p className="text-xs text-muted-foreground truncate">{position.marketTitle}</p>
        </div>

        <div className="mb-2">
          <p className="text-sm">
            {position.side}: {position.quantity} @ {position.avgEntryPrice}¢
          </p>
        </div>

        <Separator className="my-2" />

        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground">P&L</p>
            <p className={`text-sm font-semibold ${pnlColor}`}>
              ${position.unrealizedPnL.toFixed(2)}
            </p>
          </div>

          <div className={`flex items-center gap-1 ${pnlColor}`}>
            <span>{pnlIcon}</span>
            <span className="text-sm font-semibold">
              {position.unrealizedPnLPercent >= 0 ? '+' : ''}
              {position.unrealizedPnLPercent.toFixed(1)}%
            </span>
          </div>
        </div>

        <div className="mt-2 text-xs text-muted-foreground">
          Current: {position.currentPrice}¢
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## Data Flow

### 1. **Authentication Flow**

```
User enters API key in frontend
    ↓
POST /api/v1/account/authenticate { api_key: "..." }
    ↓
Backend: Validate API key with Kalshi
    ↓
Backend: Encrypt and store in PostgreSQL (user_credentials table)
    ↓
Backend: Generate JWT session token
    ↓
Frontend: Store JWT in httpOnly cookie
    ↓
Frontend: Redirect to dashboard with position panel enabled
```

### 2. **Initial Position Load Flow**

```
Frontend: Page load → usePositions() hook
    ↓
GET /api/v1/account/positions (with JWT cookie)
    ↓
Backend: Lookup user credentials from database
    ↓
Backend: Decrypt API key
    ↓
Backend: Call Kalshi GET /portfolio/positions
    ↓
Backend: Initialize PositionTracker with positions
    ↓
Backend: Return positions array to frontend
    ↓
Frontend: Display in PositionPanel
```

### 3. **Real-time Update Flow (SSE)**

```
Kalshi: Market price changes
    ↓
Kalshi WebSocket: Pushes "market_price_updated" event
    ↓
Backend StreamingManager: Receives event
    ↓
Backend PositionTracker: Updates position.current_price
    ↓
Backend PositionTracker: Recalculates P&L
    ↓
Backend StreamingManager: Pushes to all SSE client queues
    ↓
Backend SSE endpoint: Yields event to EventSource clients
    ↓
Frontend usePositionSSE: Receives SSE event
    ↓
Frontend positionsStore: Updates position state
    ↓
UI: PositionCard re-renders with new P&L (animated)
```

---

## Security Architecture

### Threat Model

| Threat | Mitigation |
|--------|------------|
| **API key exposure** | Encrypted storage, never sent to frontend after initial auth |
| **Man-in-the-middle** | HTTPS only, WebSocket over TLS (WSS) |
| **Unauthorized access** | JWT session tokens, httpOnly cookies |
| **Database breach** | Fernet encryption (AES-128), rotate encryption keys |
| **Replay attacks** | JWT expiration (24h), WebSocket connection auth |
| **XSS attacks** | Content Security Policy, input sanitization |

### Encryption Details

**Fernet (Symmetric Encryption)**:
- Algorithm: AES-128-CBC with HMAC-SHA256 authentication
- Key derivation: PBKDF2-HMAC-SHA256 (if password-based)
- Secret key storage: Environment variable (`ENCRYPTION_SECRET_KEY`)
- Key rotation: Manual process (decrypt with old key, re-encrypt with new key)

**JWT Session Tokens**:
- Algorithm: HS256 (HMAC-SHA256)
- Payload: `{ user_id: string, exp: timestamp }`
- Storage: httpOnly cookie (not accessible to JavaScript)
- Expiration: 24 hours
- Renewal: Automatic on API requests if > 20 hours old

---

## SSE Architecture

### Connection Lifecycle

```
┌─────────────────────────────────────────────────────────┐
│         Frontend EventSource Client (Browser)           │
└───────────────────┬─────────────────────────────────────┘
                    │ 1. Connect to SSE endpoint (JWT in query)
                    ↓
┌─────────────────────────────────────────────────────────┐
│         Backend SSE Endpoint (FastAPI)                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 2. Authenticate JWT                              │   │
│  │ 3. Create dedicated update queue                 │   │
│  │ 4. Send initial positions snapshot               │   │
│  │ 5. Start SSE stream generator                    │   │
│  └──────────────────────────────────────────────────┘   │
└───────────────────┬─────────────────────────────────────┘
                    │ 6. Backend maintains Kalshi WebSocket
                    ↓
┌─────────────────────────────────────────────────────────┐
│         Kalshi WebSocket (upstream)                     │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 7. Authenticated with user API key               │   │
│  │ 8. Subscribed to: portfolio, positions           │   │
│  └──────────────────────────────────────────────────┘   │
└───────────────────┬─────────────────────────────────────┘
                    │ 9. Market event occurs
                    ↓
┌─────────────────────────────────────────────────────────┐
│         Backend Event Handler                           │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 10. Update PositionTracker state                 │   │
│  │ 11. Recalculate P&L                              │   │
│  │ 12. Push to all SSE client queues                │   │
│  └──────────────────────────────────────────────────┘   │
└───────────────────┬─────────────────────────────────────┘
                    │ 13. Position update event
                    ↓
┌─────────────────────────────────────────────────────────┐
│         Frontend EventSource Client                     │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 14. Receive SSE event                            │   │
│  │ 15. Parse JSON from event.data                   │   │
│  │ 16. Update Zustand store                         │   │
│  │ 17. Trigger UI re-render                         │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Message Protocol

**Backend → Frontend SSE Events**:
```typescript
type SSEMessage =
  | { type: 'snapshot', positions: Position[] }           // Initial load
  | { type: 'position_update', data: Position }           // Single position change
  | { type: 'position_removed', ticker: string }          // Position closed
  | { type: 'portfolio_update', data: Portfolio }         // Balance/total change
  | { type: 'connection_status', status: string }         // Connection state
  | { type: 'error', message: string };                   // Error notification
```

**Reconnection Strategy**:
- **Frontend (EventSource)**: Browser automatic reconnection (built-in)
- **Backend ↔ Kalshi**: Exponential backoff (2s, 4s, 8s, 16s, 32s max)
- **Connection recovery**: Browser retries SSE connection automatically
- **Error handling**: EventSource `onerror` event triggers UI status update

---

## Database Schema

### New Tables

#### `user_credentials`
```sql
CREATE TABLE user_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) UNIQUE NOT NULL,  -- For Phase 1, single user: "default"
    encrypted_api_key TEXT NOT NULL,        -- Fernet-encrypted Kalshi API key
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_credentials_user_id ON user_credentials(user_id);
```

#### `position_cache` (Optional - for offline mode)
```sql
CREATE TABLE position_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    ticker VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('YES', 'NO')),
    quantity INTEGER NOT NULL,
    avg_entry_price INTEGER NOT NULL,  -- cents
    current_price INTEGER NOT NULL,     -- cents
    entry_time TIMESTAMP NOT NULL,
    cached_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, ticker)
);

CREATE INDEX idx_position_cache_user_ticker ON position_cache(user_id, ticker);
```

---

## API Specification

### REST Endpoints

#### `POST /api/v1/account/authenticate`
**Purpose**: Store user API key and establish session

**Request**:
```json
{
  "api_key": "kalshi_api_key_abc123..."  // pragma: allowlist secret
}
```

**Response** (200 OK):
```json
{
  "status": "authenticated",
  "user_id": "default",
  "session_expires_at": "2025-10-05T17:30:00Z"
}
```

**Response** (401 Unauthorized):
```json
{
  "error": "invalid_credentials",
  "message": "Failed to authenticate with Kalshi API"
}
```

---

#### `GET /api/v1/account/portfolio`
**Purpose**: Get portfolio snapshot

**Headers**: `Authorization: Bearer <JWT>`

**Response** (200 OK):
```json
{
  "total_value": 10245.32,
  "cash_balance": 5120.00,
  "today_pnl": 127.50,
  "today_pnl_percent": 1.26,
  "total_pnl": 245.32,
  "position_count": 5,
  "last_updated": "2025-10-04T17:30:15Z"
}
```

---

#### `GET /api/v1/account/positions`
**Purpose**: Get all open positions

**Headers**: `Authorization: Bearer <JWT>`

**Response** (200 OK):
```json
{
  "positions": [
    {
      "id": "pos_123",
      "ticker": "INXD-25JAN01",
      "market_title": "S&P 500 closes above 4500 on Jan 1",
      "side": "YES",
      "quantity": 100,
      "avg_entry_price": 68,
      "current_price": 71,
      "unrealized_pnl": 3.00,
      "unrealized_pnl_percent": 4.41,
      "duration_held": 86400,
      "entry_time": "2025-10-03T17:30:00Z",
      "expiration_date": "2025-01-01T21:00:00Z",
      "last_updated": "2025-10-04T17:30:15Z"
    }
  ]
}
```

---

#### `DELETE /api/v1/account/logout`
**Purpose**: Clear stored credentials and invalidate session

**Headers**: `Authorization: Bearer <JWT>`

**Response** (200 OK):
```json
{
  "status": "logged_out"
}
```

---

### SSE Endpoint

#### `GET /api/v1/account/sse/positions?token=<JWT>`
**Purpose**: Server-Sent Events stream for real-time position updates

**Connection** (Frontend):
```typescript
const eventSource = new EventSource(
  `/api/v1/account/sse/positions?token=${jwtToken}`
);

eventSource.onmessage = (event) => {
  const update = JSON.parse(event.data);
  positionsStore.handleUpdate(update);
};

eventSource.onerror = () => {
  // Browser automatically reconnects
  setConnectionStatus('reconnecting');
};
```

**Implementation** (Backend):
```python
from fastapi.responses import StreamingResponse

@router.get("/account/sse/positions")
async def position_stream(token: str = Query(...)):
    """SSE endpoint for real-time position updates."""
    user_id = authenticate_jwt(token)

    return StreamingResponse(
        streaming_manager.position_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**Events Sent**:
See [Message Protocol](#message-protocol) above

---

## Deployment Architecture

### Phase 1: Local Development (Current)
**No changes required** - runs in Docker Compose

### Phase 2: Cloud Deployment (Future)
When deploying to GCP, additional considerations:

**Secret Management**:
```yaml
# Add to Cloud Run environment
ENCRYPTION_SECRET_KEY: ${secret:encryption-key}  # From Secret Manager
```

**Database Migration**:
```bash
# Run Alembic migrations on Cloud SQL
alembic upgrade head
```

**SSE Scaling**:
- Use **Cloud Run with streaming support** (native SSE support)
- No sticky sessions needed (stateless SSE endpoints)
- Shared state via **Redis** for PositionTracker (if scaling >1 instance)

---

## Performance Considerations

### Latency Targets

| Operation | Target | Acceptable |
|-----------|--------|------------|
| Position API fetch | < 200ms | < 500ms |
| WebSocket message (Kalshi → Backend) | < 100ms | < 200ms |
| SSE event (Backend → Frontend) | < 100ms | < 200ms |
| P&L calculation | < 10ms | < 50ms |
| Frontend UI update | < 16ms (60fps) | < 33ms (30fps) |

### Optimization Strategies

**Backend**:
- **In-memory position state** (no database round-trip for P&L)
- **Batch price updates** (if Kalshi sends high-frequency updates)
- **Connection pooling** (reuse PostgreSQL connections)
- **Async I/O** (FastAPI + asyncio for non-blocking operations)

**Frontend**:
- **Virtual scrolling** (if >50 positions)
- **Debounced updates** (if price updates >10/sec)
- **React.memo** for PositionCard components
- **CSS transforms** for P&L animations (hardware-accelerated)

**SSE Streaming**:
- **Event compression** (gzip for large position snapshots)
- **Queue management** (bounded queues to prevent memory growth)
- **Efficient serialization** (orjson for faster JSON encoding)

---

## Migration Strategy

### Phase 1: Backend Foundation (Week 1)
**Goal**: Authentication + REST endpoints work

**Steps**:
1. Add `user_credentials` table migration
2. Implement `CredentialManager`
3. Implement `AuthenticatedKalshiClient`
4. Add `/account/authenticate` endpoint
5. Add `/account/positions` endpoint
6. Test with Postman/curl

**Testing**:
- Unit tests for encryption/decryption
- Integration test for Kalshi API authentication
- End-to-end test: store key → fetch positions

---

### Phase 2: Real-time Infrastructure (Week 2)
**Goal**: SSE streaming functional

**Steps**:
1. Implement `PositionTracker`
2. Implement `StreamingManager` (Kalshi WebSocket + SSE)
3. Add `/account/sse/positions` endpoint
4. Test Kalshi WebSocket subscription
5. Test backend → frontend SSE flow

**Testing**:
- Mock Kalshi WebSocket events
- Test reconnection logic (both Kalshi WS and SSE)
- Load test: 50 positions, 100 price updates/min

---

### Phase 3: Frontend Integration (Week 3)
**Goal**: Production-ready UI

**Steps**:
1. Add Zustand stores
2. Implement `usePositionSSE` hook (EventSource)
3. Build `PortfolioSummaryBar`
4. Build `PositionPanel` + `PositionCard`
5. Integrate with existing dashboard layout

**Testing**:
- Component tests (Vitest)
- E2E tests (Playwright)
- Visual regression tests

---

## Open Questions for Refinement

1. **Multi-user support**: Build for single user now, or anticipate multi-user from start?
   - **Recommendation**: Single user (`user_id = "default"`) for Phase 1, migrate later

2. **Position history**: Store historical positions in database for later analysis?
   - **Recommendation**: Not in Phase 1 - add in Phase 4 (multi-user SaaS)

3. **Order placement**: Should position panel include "Quick close" buttons?
   - **Recommendation**: Not in Phase 1 - view-only monitoring

4. **Mobile responsive**: Position panel on mobile?
   - **Recommendation**: Desktop-first, responsive if time permits

5. **Notifications**: Browser notifications for P&L alerts?
   - **Recommendation**: Phase 4 feature

---

## Summary

### Key Architectural Principles Maintained
✅ **Type safety** - Pydantic + TypeScript throughout
✅ **PostgreSQL foundation** - Minimal new tables (2), reuse existing infrastructure
✅ **Docker from day 1** - No new deployment complexity
✅ **Phased complexity** - Real-time only where justified (positions), not everywhere

### Complexity Introduced
⚠️ **SSE streaming** - Kalshi WebSocket upstream, SSE downstream, queue management
⚠️ **Encryption layer** - Credential security adds complexity
⚠️ **Stateful backend** - PositionTracker maintains in-memory state

### Risk Mitigation
🛡️ **Graceful degradation** - Falls back to REST polling if SSE fails
🛡️ **Write-through cache** - Position cache in database as source of truth
🛡️ **Security-first** - Encrypted credentials, JWT sessions, HTTPS/TLS only
🛡️ **Browser auto-reconnect** - EventSource handles reconnection automatically

---

**Ready for implementation?** Review this architecture, then proceed to Phase 1 development!
