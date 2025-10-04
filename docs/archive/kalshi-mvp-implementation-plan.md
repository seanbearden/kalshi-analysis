# Kalshi Hybrid SDK - Phase 1 MVP Implementation Plan

## Overview

**Objective**: Implement hybrid Kalshi SDK integration with WebSocket-powered real-time updates for Phase 1 MVP.

**Timeline Estimate**: 2-3 weeks for full MVP
**Tech Stack**: FastAPI (backend) + React/TypeScript (frontend) + PostgreSQL + Kalshi SDKs

---

## Implementation Phases

### Phase 1A: Backend Foundation (Week 1)
**Goal**: Set up backend with Python SDK, database, and GraphQL API

#### Task 1.1: Backend Setup & Dependencies
- [ ] Install `kalshi-python` SDK
- [ ] Install `strawberry-graphql[fastapi]` for GraphQL
- [ ] Set up async SQLAlchemy with PostgreSQL
- [ ] Configure environment variables (.env)
- [ ] Create backend project structure

**Files to Create**:
```
backend/
├── api/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── schema.py               # Strawberry GraphQL schema
│   └── resolvers/
│       ├── __init__.py
│       ├── market_resolvers.py
│       ├── order_resolvers.py
│       └── portfolio_resolvers.py
├── services/
│   ├── __init__.py
│   ├── kalshi_service.py       # Kalshi SDK wrapper
│   └── websocket_service.py    # WebSocket management
├── db/
│   ├── __init__.py
│   ├── models.py               # SQLAlchemy models
│   └── session.py              # Database session
├── .env
└── requirements.txt
```

**Acceptance Criteria**:
- Backend starts on `localhost:8000`
- GraphQL playground accessible at `/graphql`
- Database connection verified

---

#### Task 1.2: Kalshi Python SDK Integration
- [ ] Create `KalshiService` class in `services/kalshi_service.py`
- [ ] Implement authentication (API key ID + private key)
- [ ] Create methods for:
  - `get_markets()` - List available markets
  - `get_market(ticker)` - Get single market details
  - `place_order()` - Place order
  - `get_portfolio()` - Get user portfolio
  - `get_order_history()` - Get past orders

**Code Skeleton**:
```python
# services/kalshi_service.py
from kalshi_python import KalshiClient
import os

class KalshiService:
    def __init__(self):
        self.client = KalshiClient(
            api_key_id=os.getenv('KALSHI_API_KEY_ID'),
            private_key_path=os.getenv('KALSHI_PRIVATE_KEY_PATH'),
            base_url=os.getenv('KALSHI_API_BASE', 'https://demo-api.kalshi.com')
        )

    async def get_markets(self, status: str = 'active'):
        return await self.client.get_markets(status=status)

    async def place_order(self, ticker: str, side: str, quantity: int, price: int):
        return await self.client.place_order(
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=price
        )

    # ... more methods
```

**Acceptance Criteria**:
- Successfully fetch markets from Kalshi demo API
- Place test order (with demo credentials)
- Retrieve portfolio data

---

#### Task 1.3: Database Models & Migrations
- [ ] Create SQLAlchemy models for:
  - `Order` (id, market_id, side, quantity, price, status, created_at)
  - `Trade` (id, order_id, fill_price, fill_quantity, executed_at)
  - `PortfolioSnapshot` (id, total_value, positions_json, captured_at)
- [ ] Set up Alembic for migrations
- [ ] Create initial migration

**Code Skeleton**:
```python
# db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Order(Base):
    __tablename__ = 'orders'

    id = Column(String, primary_key=True)
    market_id = Column(String, nullable=False)
    side = Column(String, nullable=False)  # 'YES' or 'NO'
    quantity = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)

class Trade(Base):
    __tablename__ = 'trades'

    id = Column(String, primary_key=True)
    order_id = Column(String, nullable=False)
    fill_price = Column(Integer, nullable=False)
    fill_quantity = Column(Integer, nullable=False)
    executed_at = Column(DateTime, default=datetime.utcnow)

class PortfolioSnapshot(Base):
    __tablename__ = 'portfolio_snapshots'

    id = Column(Integer, primary_key=True, autoincrement=True)
    total_value = Column(Float, nullable=False)
    positions_json = Column(JSON, nullable=False)
    captured_at = Column(DateTime, default=datetime.utcnow)
```

**Acceptance Criteria**:
- Tables created in PostgreSQL
- Migrations run successfully
- Can insert/query test data

---

#### Task 1.4: GraphQL Schema & Resolvers
- [ ] Define GraphQL types (Market, Order, Portfolio)
- [ ] Implement queries:
  - `markets(filter: MarketFilter): [Market!]!`
  - `market(id: ID!): Market`
  - `portfolio: Portfolio!`
  - `orderHistory: [Order!]!`
- [ ] Implement mutations:
  - `placeOrder(input: OrderInput!): Order!`
  - `cancelOrder(orderId: ID!): Boolean!`

**Code Skeleton**:
```python
# api/schema.py
import strawberry
from typing import List, Optional

@strawberry.type
class Market:
    id: str
    ticker: str
    title: str
    yes_price: int
    no_price: int
    volume: int

@strawberry.input
class OrderInput:
    market_id: str
    side: str
    quantity: int
    price: int

@strawberry.type
class Order:
    id: str
    market_id: str
    side: str
    quantity: int
    price: int
    status: str

@strawberry.type
class Query:
    @strawberry.field
    async def markets(self, status: Optional[str] = 'active') -> List[Market]:
        kalshi_service = KalshiService()
        markets = await kalshi_service.get_markets(status)
        return [Market(**m) for m in markets]

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def place_order(self, input: OrderInput) -> Order:
        kalshi_service = KalshiService()
        order = await kalshi_service.place_order(
            ticker=input.market_id,
            side=input.side,
            quantity=input.quantity,
            price=input.price
        )
        # Save to database
        # ...
        return Order(**order)

schema = strawberry.Schema(query=Query, mutation=Mutation)
```

**Acceptance Criteria**:
- GraphQL queries return data from Kalshi
- Mutations create orders and persist to database
- GraphQL playground works with sample queries

---

#### Task 1.5: Backend WebSocket Service (Fill Notifications)
- [ ] Create `WebSocketService` class
- [ ] Implement authenticated WebSocket connection to Kalshi
- [ ] Subscribe to `fills` channel
- [ ] Process fill notifications and update database
- [ ] (Future) Push updates to frontend via GraphQL subscriptions

**Code Skeleton**:
```python
# services/websocket_service.py
import asyncio
from kalshi_python import KalshiWebSocketClient
from db.models import Order, Trade
from db.session import AsyncSessionLocal

class WebSocketService:
    def __init__(self):
        self.ws_client = KalshiWebSocketClient(
            api_key_id=os.getenv('KALSHI_API_KEY_ID'),
            private_key_path=os.getenv('KALSHI_PRIVATE_KEY_PATH')
        )

    async def subscribe_to_fills(self):
        async with self.ws_client.connect() as ws:
            await ws.subscribe({'type': 'fills'})

            async for message in ws:
                if message['type'] == 'fill':
                    await self._handle_fill(message)

    async def _handle_fill(self, fill_message):
        async with AsyncSessionLocal() as session:
            # Update order status
            order = await session.get(Order, fill_message['order_id'])
            order.status = 'filled'

            # Create trade record
            trade = Trade(
                id=fill_message['fill_id'],
                order_id=fill_message['order_id'],
                fill_price=fill_message['price'],
                fill_quantity=fill_message['quantity']
            )
            session.add(trade)
            await session.commit()

            print(f"Order {order.id} filled at ${fill_message['price']}")

# Start WebSocket service in background
async def start_websocket_service():
    ws_service = WebSocketService()
    await ws_service.subscribe_to_fills()
```

**Acceptance Criteria**:
- WebSocket connects to Kalshi demo environment
- Receives fill notifications when test orders execute
- Database updates automatically on fills

---

### Phase 1B: Frontend Foundation (Week 2)
**Goal**: Set up frontend with TypeScript SDK and WebSocket subscriptions

#### Task 2.1: Frontend Setup & Dependencies
- [ ] Install `kalshi-typescript` SDK
- [ ] Install `@apollo/client` for GraphQL
- [ ] Set up React project structure
- [ ] Configure environment variables (.env.local)

**Files to Create**:
```
frontend/
├── src/
│   ├── lib/
│   │   ├── kalshi.ts              # TypeScript SDK client
│   │   ├── apollo.ts              # Apollo client setup
│   │   └── websocket.ts           # WebSocket hooks
│   ├── components/
│   │   ├── MarketsPage.tsx
│   │   ├── MarketCard.tsx
│   │   ├── OrderForm.tsx
│   │   ├── PortfolioPage.tsx
│   │   └── ConnectionStatus.tsx
│   ├── hooks/
│   │   ├── useKalshiWebSocket.ts
│   │   └── useMarketData.ts
│   ├── App.tsx
│   └── main.tsx
├── .env.local
└── package.json
```

**Acceptance Criteria**:
- Frontend runs on `localhost:5173`
- TypeScript SDK imported successfully
- Apollo Client connects to backend GraphQL

---

#### Task 2.2: TypeScript SDK REST Integration
- [ ] Create Kalshi client wrapper in `lib/kalshi.ts`
- [ ] Implement `getMarkets()` method
- [ ] Implement `getMarket(id)` method
- [ ] Create React hook `useMarketData()`

**Code Skeleton**:
```typescript
// lib/kalshi.ts
import { KalshiClient } from 'kalshi-typescript';

export const kalshiClient = new KalshiClient({
  apiKey: import.meta.env.VITE_KALSHI_READ_ONLY_KEY,
  baseUrl: 'https://demo-api.kalshi.com'
});

export async function getMarkets(status: string = 'active') {
  return await kalshiClient.getMarkets({ status });
}

// hooks/useMarketData.ts
import { useState, useEffect } from 'react';
import { getMarkets } from '../lib/kalshi';

export function useMarketData() {
  const [markets, setMarkets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMarkets = async () => {
      const data = await getMarkets();
      setMarkets(data);
      setLoading(false);
    };
    fetchMarkets();
  }, []);

  return { markets, loading };
}
```

**Acceptance Criteria**:
- Markets display in UI from TypeScript SDK
- Loading states work correctly
- Error handling for failed requests

---

#### Task 2.3: Frontend WebSocket Integration
- [ ] Create `useKalshiWebSocket` hook
- [ ] Implement ticker subscription for real-time prices
- [ ] Implement order book subscription
- [ ] Add reconnection logic with exponential backoff
- [ ] Create `ConnectionStatus` component

**Code Skeleton**:
```typescript
// hooks/useKalshiWebSocket.ts
import { useState, useEffect, useCallback } from 'react';
import { KalshiWebSocketClient } from 'kalshi-typescript';

type ConnectionState = 'connected' | 'reconnecting' | 'failed';

export function useKalshiWebSocket(marketId: string) {
  const [price, setPrice] = useState<{ yes: number; no: number } | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>('connected');

  useEffect(() => {
    const wsClient = new KalshiWebSocketClient({
      apiKey: import.meta.env.VITE_KALSHI_READ_ONLY_KEY,
      endpoint: 'wss://demo-api.kalshi.co/trade-api/ws/v2'
    });

    let retries = 0;
    const maxRetries = 5;

    const connect = async () => {
      try {
        await wsClient.connect();
        setConnectionState('connected');
        retries = 0;

        // Subscribe to ticker updates
        await wsClient.subscribe({
          type: 'ticker',
          market_ticker: marketId
        }, (message) => {
          setPrice({
            yes: message.yes_price,
            no: message.no_price
          });
        });

      } catch (error) {
        retries++;
        if (retries < maxRetries) {
          setConnectionState('reconnecting');
          const delay = Math.min(1000 * Math.pow(2, retries), 30000);
          setTimeout(connect, delay);
        } else {
          setConnectionState('failed');
        }
      }
    };

    connect();

    return () => {
      wsClient.disconnect();
    };
  }, [marketId]);

  return { price, connectionState };
}
```

**Acceptance Criteria**:
- Real-time price updates display in UI
- Reconnection works after temporary disconnection
- Connection status visible to user

---

#### Task 2.4: Apollo GraphQL Integration
- [ ] Set up Apollo Client in `lib/apollo.ts`
- [ ] Create GraphQL queries (GET_MARKETS, GET_PORTFOLIO)
- [ ] Create GraphQL mutations (PLACE_ORDER, CANCEL_ORDER)
- [ ] Implement optimistic updates for order placement

**Code Skeleton**:
```typescript
// lib/apollo.ts
import { ApolloClient, InMemoryCache, createHttpLink } from '@apollo/client';

const httpLink = createHttpLink({
  uri: import.meta.env.VITE_API_URL || 'http://localhost:8000/graphql',
});

export const apolloClient = new ApolloClient({
  link: httpLink,
  cache: new InMemoryCache(),
});

// queries.ts
import { gql } from '@apollo/client';

export const PLACE_ORDER_MUTATION = gql`
  mutation PlaceOrder($input: OrderInput!) {
    placeOrder(input: $input) {
      id
      marketId
      side
      quantity
      price
      status
    }
  }
`;

export const GET_PORTFOLIO = gql`
  query GetPortfolio {
    portfolio {
      totalValue
      positions {
        marketId
        quantity
        entryPrice
      }
    }
  }
`;
```

**Acceptance Criteria**:
- Order placement works via GraphQL mutation
- Portfolio displays from backend
- Optimistic UI updates feel instant

---

#### Task 2.5: UI Components
- [ ] Create `MarketsPage` - Browse markets with WebSocket prices
- [ ] Create `MarketCard` - Individual market display with live price
- [ ] Create `OrderForm` - Place orders with validation
- [ ] Create `PortfolioPage` - Display positions and P&L
- [ ] Create `ConnectionStatus` - Show WebSocket connection state

**Code Skeleton**:
```typescript
// components/MarketCard.tsx
import { useKalshiWebSocket } from '../hooks/useKalshiWebSocket';

interface MarketCardProps {
  market: {
    id: string;
    ticker: string;
    title: string;
  };
}

export function MarketCard({ market }: MarketCardProps) {
  const { price, connectionState } = useKalshiWebSocket(market.id);

  return (
    <div className="border rounded-lg p-4">
      <h3 className="font-bold">{market.title}</h3>
      <div className="flex justify-between mt-2">
        <div>
          <span className="text-green-600">YES: ${price?.yes ?? '—'}</span>
        </div>
        <div>
          <span className="text-red-600">NO: ${price?.no ?? '—'}</span>
        </div>
      </div>
      {connectionState !== 'connected' && (
        <div className="text-sm text-yellow-600 mt-1">
          {connectionState === 'reconnecting' ? '🔄 Reconnecting...' : '⚠️ Connection failed'}
        </div>
      )}
    </div>
  );
}
```

**Acceptance Criteria**:
- Markets page displays with live prices
- Order form validates input and places orders
- Portfolio shows current positions
- Connection status visible and accurate

---

### Phase 1C: Integration & Testing (Week 3)
**Goal**: End-to-end testing, error handling, and polish

#### Task 3.1: Error Handling & Fallbacks
- [ ] Implement WebSocket → GraphQL fallback on frontend
- [ ] Add toast notifications for errors
- [ ] Handle backend SDK failures gracefully
- [ ] Test reconnection scenarios

**Test Cases**:
- [ ] Frontend WebSocket fails → Falls back to backend GraphQL
- [ ] Backend Kalshi API fails → Shows user-friendly error
- [ ] Network disconnection → Automatic reconnection works
- [ ] Stale data indicator shows when using cached data

**Acceptance Criteria**:
- All error scenarios handled gracefully
- User always sees helpful error messages
- No crashes or blank screens on failures

---

#### Task 3.2: Data Persistence & Reconciliation
- [ ] Ensure all orders persist to database
- [ ] Verify fill notifications update database correctly
- [ ] Test portfolio snapshot caching
- [ ] Implement data reconciliation on reconnection

**Test Cases**:
- [ ] Order placed → Saved to database
- [ ] Fill notification received → Trade recorded
- [ ] Portfolio fetched → Snapshot cached
- [ ] Reconnection → Data syncs from Kalshi

**Acceptance Criteria**:
- No data loss during disconnections
- Database always reflects true state
- Portfolio reconciles after reconnection

---

#### Task 3.3: Performance Optimization
- [ ] Optimize WebSocket subscription management (unsubscribe on unmount)
- [ ] Implement request caching where appropriate
- [ ] Add loading states and skeletons
- [ ] Test with multiple concurrent WebSocket connections

**Optimization Targets**:
- WebSocket connections: < 100ms to first message
- Order placement: < 200ms response time
- Market list load: < 500ms initial render
- Memory usage: < 100MB for 50 active subscriptions

**Acceptance Criteria**:
- UI feels instant and responsive
- No memory leaks from WebSocket connections
- Efficient resource usage

---

#### Task 3.4: Documentation & Deployment Prep
- [ ] Document environment variables needed
- [ ] Create setup instructions in README
- [ ] Add API usage examples
- [ ] Test deployment with Docker Compose

**Documentation to Create**:
- `README.md` - Project overview and setup
- `SETUP.md` - Step-by-step installation
- `API.md` - GraphQL schema reference
- `WEBSOCKET.md` - WebSocket integration guide

**Acceptance Criteria**:
- New developer can set up project in < 30 minutes
- All configuration documented
- Docker Compose starts entire stack

---

## Environment Configuration

### Backend `.env`
```bash
# Kalshi API
KALSHI_API_KEY_ID=your_key_id
KALSHI_PRIVATE_KEY_PATH=/path/to/private_key.pem
KALSHI_API_BASE=https://demo-api.kalshi.com

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/kalshi_db  # pragma: allowlist secret

# Server
PORT=8000
```

### Frontend `.env.local`
```bash
# Kalshi TypeScript SDK
VITE_KALSHI_READ_ONLY_KEY=your_read_only_key

# Backend API
VITE_API_URL=http://localhost:8000/graphql

# WebSocket
VITE_KALSHI_WS_URL=wss://demo-api.kalshi.co/trade-api/ws/v2
```

---

## Testing Strategy

### Unit Tests
- Backend: pytest for Kalshi service methods
- Frontend: Vitest for hooks and utilities

### Integration Tests
- Backend: Test GraphQL resolvers with test database
- Frontend: Test WebSocket reconnection logic

### E2E Tests
- Test complete order flow: browse → place order → receive fill
- Test WebSocket fallback scenarios
- Test portfolio updates on fill notifications

---

## Success Metrics (Phase 1 MVP)

### Functional Requirements
- ✅ Users can browse markets with real-time prices
- ✅ Users can place orders via backend API
- ✅ Portfolio displays current positions
- ✅ Fill notifications received instantly
- ✅ WebSocket reconnection works automatically

### Technical Requirements
- ✅ WebSocket latency < 100ms
- ✅ Order placement < 200ms
- ✅ 99% uptime for WebSocket connections
- ✅ Graceful fallback on all failures
- ✅ Zero data loss during reconnections

### User Experience
- ✅ Real-time price updates feel instant
- ✅ Order placement confirms immediately
- ✅ Clear error messages on failures
- ✅ Connection status always visible
- ✅ No blank screens or crashes

---

## Next Steps After MVP

### Phase 2: Enhanced Features
- GraphQL subscriptions (wrap Kalshi WebSocket)
- Advanced order types (limit, stop-loss)
- Portfolio P&L charts
- Trade history with filters

### Phase 3: Production Readiness
- Multi-user authentication
- Encrypted credential storage
- Rate limiting and queuing
- Monitoring and alerting

### Phase 4: Data Science Integration
- Backtesting engine
- Calibration analysis
- Probability modeling
- Strategy optimization

---

## Resources

### Official Documentation
- Kalshi API Docs: https://docs.kalshi.com
- Kalshi WebSocket Guide: https://docs.kalshi.com/getting_started/quick_start_websockets
- Kalshi Python SDK: https://github.com/kalshi/kalshi-python
- Kalshi TypeScript SDK: https://github.com/kalshi/kalshi-typescript

### Technical References
- Strawberry GraphQL: https://strawberry.rocks
- Apollo Client: https://www.apollographql.com/docs/react
- SQLAlchemy Async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html

---

## Risk Mitigation

### Technical Risks
- **WebSocket disconnections**: Mitigated by exponential backoff reconnection
- **API rate limits**: Mitigated by backend caching and request queuing
- **Database failures**: Mitigated by SDK state as fallback

### Business Risks
- **Kalshi API changes**: Monitor API changelog, use versioned endpoints
- **Credential security**: Never commit keys, use environment variables
- **Data accuracy**: Reconcile with Kalshi API on reconnection

---

## Contact & Support

For questions or issues during implementation:
- Review architecture doc: `claudedocs/kalshi-hybrid-sdk-architecture.md`
- Check Kalshi Discord: https://discord.gg/kalshi
- Refer to SDK examples in official repos
