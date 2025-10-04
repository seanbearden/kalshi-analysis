# Kalshi Hybrid SDK Architecture

## Executive Summary

**Architecture Pattern**: Hybrid dual-SDK approach with backend Python SDK as source of truth and frontend TypeScript SDK for convenience layer.

**Phase**: 1 (MVP)
**Sync Strategy**: Polling with optimistic updates (Phase 1) → GraphQL Subscriptions (Phase 2+)
**Security Posture**: Development-friendly now, production-ready architecture
**Real-time Tolerance**: Delay acceptable (not sub-second critical)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │  TypeScript SDK (Read-Only Convenience Layer)      │    │
│  │  - REST: Market browsing, initial data             │    │
│  │  - WebSocket: Real-time prices, order books        │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↕                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  GraphQL Client (Apollo)                           │    │
│  │  - Trading operations (mutations)                   │    │
│  │  - Portfolio queries                                │    │
│  │  - Fallback for failed WebSocket                   │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
          ↕ HTTP/GraphQL              ↕ WebSocket
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                            │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Python SDK (Source of Truth)                      │    │
│  │  - REST: Trading, portfolio management             │    │
│  │  - WebSocket: Fill notifications (authenticated)   │    │
│  └────────────────────────────────────────────────────┘    │
│                          ↕                                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  PostgreSQL                                         │    │
│  │  - Trades, orders, portfolio snapshots              │    │
│  │  - Historical P&L data                              │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
          ↕ REST API              ↕ WebSocket
                    ┌─────────────────────────┐
                    │     Kalshi API          │
                    │  REST + WebSocket       │
                    │  wss://demo-api.kalshi. │
                    │  co/trade-api/ws/v2     │
                    └─────────────────────────┘
```

---

## Component Responsibilities

### Frontend TypeScript SDK
**Purpose**: Convenience layer for read-only market data display

**Responsibilities**:
- Browse available markets (list, filter, search)
- Display real-time prices (with acceptable delay)
- Show order book depth
- Render recent trades feed

**Does NOT Handle**:
- Authentication (credentials never reach browser)
- Order placement
- Portfolio mutations
- Trade history writes

**WebSocket Channels Used**:
- `ticker`: Real-time price updates for subscribed markets
- `orderbook_snapshot`: Initial complete order book state
- `orderbook_update`: Incremental order book changes (deltas)
- `trades`: Recent trade executions feed

**Error Handling**:
- On WebSocket failure: Fall back to backend GraphQL API
- Show connection status indicator (connected/reconnecting/failed)
- Automatic reconnection with exponential backoff (max 5 retries)
- Graceful degradation to backend-only mode

---

### Backend Python SDK
**Purpose**: Source of truth for all trading and portfolio operations

**Responsibilities**:
- Manage Kalshi API credentials (API key ID + private key)
- Sign all requests requiring authentication
- Execute trading operations (place, cancel, modify orders)
- Fetch and persist portfolio state
- Store trade history in PostgreSQL
- Provide GraphQL API for frontend queries

**WebSocket Channels Used**:
- `fills`: Authenticated channel for order fill notifications
- Subscription requires authentication (API key + private key signing)
- Pushes instant notifications when user orders execute

**Data Persistence**:
```sql
-- Core tables
orders (id, market_id, side, quantity, price, status, created_at)
trades (id, order_id, fill_price, fill_quantity, executed_at)
portfolio_snapshots (id, total_value, positions_json, captured_at)
```

**Error Handling**:
- On Kalshi API failure: Return error to frontend with user-friendly message
- On WebSocket disconnection: Reconnect with exponential backoff
- On database failure: Alert but continue (use SDK state as fallback)
- Retry logic for transient failures (with exponential backoff)

---

## Phase 1 MVP Features

### 1. Browse Markets (Frontend SDK)
```typescript
// Frontend: Direct TypeScript SDK usage
import { KalshiClient } from 'kalshi-typescript';

const client = new KalshiClient({ apiKey: 'read-only-key' }); // From env var  // pragma: allowlist secret
const markets = await client.getMarkets({ status: 'active' });
```

**GraphQL Fallback**:
```graphql
query GetMarkets($filter: MarketFilter) {
  markets(filter: $filter) {
    id
    ticker
    title
    yesPrice
    noPrice
    volume
  }
}
```

---

### 2. View Real-Time Prices (Frontend SDK - WebSocket)
```typescript
// Frontend: WebSocket subscription for live prices
const [marketData, setMarketData] = useState(null);
const [connectionState, setConnectionState] = useState<'connected' | 'reconnecting' | 'failed'>('connected');

useEffect(() => {
  const wsClient = new KalshiWebSocketClient({
    apiKey: import.meta.env.VITE_KALSHI_READ_ONLY_KEY
  });

  const connectAndSubscribe = async () => {
    try {
      await wsClient.connect();
      setConnectionState('connected');

      // Subscribe to live ticker updates
      await wsClient.subscribe({
        type: 'ticker',
        market_ticker: marketId
      }, (message) => {
        setMarketData({
          yesPrice: message.yes_price,
          noPrice: message.no_price,
          volume: message.volume,
          lastUpdate: new Date()
        });
      });

    } catch (error) {
      setConnectionState('failed');
      // Fallback to backend GraphQL query
      const { data } = await apolloClient.query({
        query: GET_MARKET,
        variables: { id: marketId }
      });
      setMarketData(data.market);
    }
  };

  connectAndSubscribe();

  return () => {
    wsClient.disconnect();
  };
}, [marketId]);
```

**UI Connection Status Indicator**:
```tsx
{connectionState === 'reconnecting' && (
  <Alert variant="warning">
    🔄 Reconnecting to real-time data...
  </Alert>
)}

{connectionState === 'failed' && (
  <Alert variant="error">
    ⚠️ Unable to connect. Showing cached prices.
  </Alert>
)}
```

---

### 3. Place Orders (Backend SDK)
```python
# Backend: FastAPI mutation resolver
from kalshi_python import KalshiClient

@strawberry.type
class Mutation:
    @strawberry.mutation
    async def place_order(
        self,
        market_id: str,
        side: OrderSide,
        quantity: int,
        price: int,
        info: Info
    ) -> Order:
        # Get authenticated Kalshi client
        client = get_kalshi_client(info.context)

        try:
            # Place order via Python SDK
            kalshi_order = await client.place_order(
                ticker=market_id,
                side=side.value,
                quantity=quantity,
                price=price
            )

            # Persist to database
            db_order = await save_order_to_db(kalshi_order)

            return Order.from_db(db_order)

        except KalshiAPIError as e:
            # Alert user with clear error message
            raise GraphQLError(f"Order failed: {e.message}")
```

**Frontend Integration**:
```typescript
const [placeOrder] = useMutation(PLACE_ORDER_MUTATION);

const handlePlaceOrder = async () => {
  try {
    const { data } = await placeOrder({
      variables: { marketId, side: 'YES', quantity: 10, price: 50 }
    });

    toast.success('Order placed successfully!');

  } catch (error) {
    // Backend SDK failure alert
    toast.error(`Failed to place order: ${error.message}`);
  }
};
```

---

### 4. View Portfolio (Backend SDK)
```python
@strawberry.type
class Query:
    @strawberry.field
    async def portfolio(self, info: Info) -> Portfolio:
        client = get_kalshi_client(info.context)

        try:
            # Fetch from Kalshi via Python SDK
            kalshi_portfolio = await client.get_portfolio()

            # Cache snapshot in PostgreSQL
            await save_portfolio_snapshot(kalshi_portfolio)

            return Portfolio.from_kalshi(kalshi_portfolio)

        except KalshiAPIError as e:
            # On failure: return last cached snapshot with staleness warning
            cached = await get_latest_portfolio_snapshot()
            return Portfolio.from_db(cached, is_stale=True)
```

**Frontend Display**:
```typescript
const { data, error } = useQuery(GET_PORTFOLIO);

if (data?.portfolio.isStale) {
  return (
    <Alert variant="warning">
      ⚠️ Portfolio data is stale. Last updated: {data.portfolio.lastUpdated}
    </Alert>
  );
}
```

---

## Sync Strategy: WebSocket Subscriptions (Phase 1)

**Decision Rationale**:
- Kalshi natively supports WebSockets for real-time data
- Push-based updates are more efficient than polling
- Immediate price updates and order book changes
- Native fill notifications when orders execute
- Both Python and TypeScript SDKs support WebSocket connections

**Kalshi WebSocket Capabilities**:
- **Endpoints**: `wss://demo-api.kalshi.co/trade-api/ws/v2`
- **Channels**: ticker, orderbook_snapshot, orderbook_update, trades, fills
- **Authentication**: Same RSA-PSS signing as REST API
- **Message Types**: Real-time market data, order book deltas, trade executions

**Implementation**:

### Frontend WebSocket (TypeScript SDK)
```typescript
// Frontend: Subscribe to market price updates
import { KalshiWebSocketClient } from 'kalshi-typescript';

const wsClient = new KalshiWebSocketClient({
  apiKey: import.meta.env.VITE_KALSHI_READ_ONLY_KEY,
  endpoint: 'wss://demo-api.kalshi.co/trade-api/ws/v2'
});

// Subscribe to ticker updates
await wsClient.subscribe({
  type: 'ticker',
  market_ticker: 'MARKET-ID'
}, (message) => {
  // Real-time price updates
  setMarketPrice({
    yes: message.yes_price,
    no: message.no_price,
    lastUpdate: new Date()
  });
});

// Subscribe to order book changes
await wsClient.subscribe({
  type: 'orderbook_snapshot',
  market_ticker: 'MARKET-ID'
}, (snapshot) => {
  setOrderBook(snapshot);
});
```

### Backend WebSocket (Python SDK)
```python
# Backend: Subscribe to fill notifications (authenticated)
import asyncio
from kalshi_python import KalshiWebSocketClient

async def subscribe_to_fills(user_id: str):
    client = KalshiWebSocketClient(
        api_key_id=os.getenv('KALSHI_API_KEY_ID'),
        private_key_path=os.getenv('KALSHI_PRIVATE_KEY_PATH')
    )

    async with client.connect() as ws:
        # Subscribe to authenticated fill channel
        await ws.subscribe({'type': 'fills'})

        async for message in ws:
            if message['type'] == 'fill':
                # Order executed - persist to database
                await save_fill_to_db(message)

                # Push update to frontend via GraphQL subscription
                await pubsub.publish(
                    f'portfolio_updates:{user_id}',
                    message
                )
```

### Reconnection Logic
```typescript
// Frontend: Automatic reconnection with exponential backoff
const connectWebSocket = async () => {
  let retries = 0;
  const maxRetries = 5;

  while (retries < maxRetries) {
    try {
      await wsClient.connect();
      setConnectionState('connected');
      retries = 0; // Reset on success
      break;

    } catch (error) {
      retries++;
      const delay = Math.min(1000 * Math.pow(2, retries), 30000);

      setConnectionState('reconnecting');
      console.warn(`WebSocket disconnected. Retry ${retries}/${maxRetries} in ${delay}ms`);

      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  if (retries >= maxRetries) {
    setConnectionState('failed');
    // Fallback to backend GraphQL queries
    toast.error('Unable to connect to real-time data. Using cached prices.');
  }
};
```

### Error Handling
```python
# Backend: Handle WebSocket errors
async def handle_ws_connection(market_id: str):
    try:
        async with client.connect() as ws:
            await ws.subscribe({'type': 'ticker', 'market_ticker': market_id})

            async for message in ws:
                if message.get('type') == 'error':
                    logger.error(f"WebSocket error: {message['code']} - {message['msg']}")

                    # Error codes from Kalshi docs
                    if message['code'] == 'unauthorized':
                        # Re-authenticate
                        await client.refresh_auth()

                    elif message['code'] == 'invalid_subscription':
                        # Market might have closed
                        logger.warning(f"Invalid subscription for {market_id}")
                        break

    except ConnectionClosed:
        # Reconnect with exponential backoff
        await asyncio.sleep(2 ** retry_count)
        await handle_ws_connection(market_id)
```

**Future Enhancement: GraphQL Subscriptions (Phase 2)**
```graphql
# Optional: Wrap Kalshi WebSocket with GraphQL subscriptions
type Subscription {
  portfolioUpdates: Portfolio
  orderUpdates(orderId: ID!): Order
  marketPriceUpdates(marketId: ID!): MarketPrice
}

# Implementation bridges Kalshi WS → GraphQL subscription
```

---

## Security Architecture

### Phase 1 (Local Development)
**Current Requirements**: Low security barrier for rapid development

**Implementation**:
```python
# backend/.env (NOT committed to git)
KALSHI_API_KEY_ID=your_key_id
KALSHI_PRIVATE_KEY_PATH=/path/to/private_key.pem

# Single system account for all users
def get_kalshi_client(context) -> KalshiClient:
    return KalshiClient(
        api_key_id=os.getenv('KALSHI_API_KEY_ID'),
        private_key_path=os.getenv('KALSHI_PRIVATE_KEY_PATH')
    )
```

**Frontend SDK** (read-only):
```typescript
// frontend/.env.local (NOT committed)
VITE_KALSHI_READ_ONLY_KEY=your_read_only_key

const client = new KalshiClient({
  apiKey: import.meta.env.VITE_KALSHI_READ_ONLY_KEY
});
```

---

### Phase 2+ (Production Deployment)
**Future Requirements**: Secure financial data, multi-user support

**Architecture Changes**:
1. **User Authentication**:
   ```python
   # Map authenticated users to their Kalshi credentials
   async def get_user_kalshi_client(user_id: str) -> KalshiClient:
       credentials = await fetch_encrypted_user_credentials(user_id)
       return KalshiClient(
           api_key_id=credentials.api_key_id,
           private_key=decrypt_private_key(credentials.encrypted_key)
       )
   ```

2. **Credential Encryption**:
   - Store user Kalshi credentials encrypted in PostgreSQL
   - Use AWS KMS, HashiCorp Vault, or similar for key management
   - Never log or expose private keys

3. **Frontend SDK Removal**:
   - Remove direct Kalshi API access from browser
   - All market data flows through backend (prevents credential exposure)
   - Backend caches market data to reduce Kalshi API load

4. **Rate Limiting**:
   - Implement per-user rate limits on GraphQL API
   - Respect Kalshi API rate limits at backend layer
   - Queue orders during high traffic periods

---

## Error Handling Patterns

### Backend SDK Failure
```python
@strawberry.mutation
async def place_order(...) -> Order:
    try:
        kalshi_order = await client.place_order(...)
    except KalshiConnectionError as e:
        # Network/API unavailable
        raise GraphQLError(
            "Unable to connect to Kalshi. Please try again.",
            extensions={"code": "KALSHI_UNAVAILABLE"}
        )
    except KalshiValidationError as e:
        # Invalid order parameters
        raise GraphQLError(
            f"Invalid order: {e.message}",
            extensions={"code": "INVALID_ORDER", "details": e.details}
        )
    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error placing order: {e}")
        raise GraphQLError("An unexpected error occurred. Please contact support.")
```

### Frontend SDK Failure
```typescript
const fetchMarkets = async () => {
  try {
    // Try TypeScript SDK first
    const markets = await kalshiClient.getMarkets();
    setMarkets(markets);
    setIsStale(false);

  } catch (error) {
    console.warn('TypeScript SDK failed, falling back to backend:', error);

    // Fallback to backend GraphQL
    const { data } = await apolloClient.query({ query: GET_MARKETS });
    setMarkets(data.markets);
    setIsStale(true);

    // Show warning to user
    toast.warning('Using cached market data due to connectivity issues.');
  }
};
```

---

## Implementation Phases

### Phase 1: MVP (Current)
**Scope**: Core functionality with hybrid SDK pattern

**Tasks**:
1. ✅ Backend Python SDK integration
   - Install `kalshi-python`
   - Configure authentication (API key + private key)
   - Create Kalshi service layer in FastAPI

2. ✅ GraphQL Schema for trading operations
   ```graphql
   type Market {
     id: ID!
     ticker: String!
     title: String!
     yesPrice: Int!
     noPrice: Int!
     volume: Int!
   }

   type Order {
     id: ID!
     marketId: String!
     side: OrderSide!
     quantity: Int!
     price: Int!
     status: OrderStatus!
   }

   type Portfolio {
     totalValue: Float!
     positions: [Position!]!
     isStale: Boolean!
   }

   type Mutation {
     placeOrder(input: OrderInput!): Order!
     cancelOrder(orderId: ID!): Boolean!
   }

   type Query {
     markets(filter: MarketFilter): [Market!]!
     portfolio: Portfolio!
     orderHistory: [Order!]!
   }
   ```

3. ✅ Frontend TypeScript SDK integration
   - Install `kalshi-typescript`
   - Configure read-only API key
   - Implement market browsing UI components

4. ✅ WebSocket subscriptions & connection management
   - Real-time ticker updates (via TS SDK WebSocket)
   - Fill notifications (via Python SDK WebSocket)
   - Reconnection logic with exponential backoff
   - Connection status indicators in UI

5. ✅ Error handling & user alerts
   - Toast notifications for backend failures
   - Fallback to GraphQL when TS SDK fails
   - Clear error messages for order failures

6. ✅ PostgreSQL persistence
   - Orders table
   - Trades table
   - Portfolio snapshots table

---

### Phase 2: Enhanced Real-Time (Future)
**Scope**: Upgrade to GraphQL Subscriptions for lower latency

**Tasks**:
- Implement GraphQL subscriptions (Strawberry + WebSocket)
- Backend pushes portfolio updates on order fills
- Frontend subscribes to real-time price feeds
- Remove polling, switch to event-driven updates

---

### Phase 3: Production Security (Future)
**Scope**: Multi-user support with secure credential management

**Tasks**:
- User authentication system (JWT)
- Per-user Kalshi credential storage (encrypted)
- Remove frontend TypeScript SDK (backend-only access)
- Implement rate limiting and queuing
- Add audit logging for all trading operations

---

## Data Flow Examples

### Example 1: Browse Markets (REST → WebSocket)
```
1. User visits markets page
   ↓
2. Frontend: Initial fetch via TypeScript SDK REST
   kalshiClient.getMarkets() → Kalshi API
   ↓
3. Frontend: Establish WebSocket connection
   wsClient.connect() → wss://demo-api.kalshi.co/trade-api/ws/v2
   ↓
4. Frontend: Subscribe to ticker updates for visible markets
   wsClient.subscribe({ type: 'ticker', market_ticker: 'MARKET-*' })
   ↓
5. Display markets + receive real-time price updates
   - Initial data from REST
   - Live updates via WebSocket
   ↓
6. On WebSocket failure:
   - Fallback to backend GraphQL query
   - Show "Using cached prices" warning
```

### Example 2: Place Order (with Fill Notification)
```
1. User submits order form
   ↓
2. Frontend: Send GraphQL mutation to backend
   Apollo Client → FastAPI GraphQL endpoint
   ↓
3. Backend: Validate & execute via Python SDK
   - Authenticate with Kalshi (RSA-PSS signing)
   - Place order via Python SDK
   - Kalshi API processes order
   ↓
4. Backend: Persist to database + Subscribe to fills
   - Save order to PostgreSQL
   - WebSocket subscribes to 'fills' channel (authenticated)
   - Return order confirmation to frontend
   ↓
5. Frontend: Update UI optimistically
   - Show order as "pending"
   ↓
6. Backend WebSocket: Receive fill notification
   - Kalshi pushes fill message via WebSocket
   - Update order status in database
   - Push update to frontend (via future GraphQL subscription)
   ↓
7. Frontend: Display fill confirmation
   - "Order filled at $X" notification
   - Update portfolio display
```

### Example 3: View Portfolio (with Real-Time Updates)
```
1. User navigates to portfolio page
   ↓
2. Frontend: Query backend GraphQL for initial state
   Apollo Client → GET_PORTFOLIO query
   ↓
3. Backend: Fetch from Kalshi via Python SDK
   - Get current positions
   - Calculate total P&L
   - Cache snapshot in PostgreSQL
   ↓
4. Backend: Subscribe to fill notifications via WebSocket
   - Python SDK WebSocket connects
   - Subscribe to authenticated 'fills' channel
   ↓
5. Frontend: Display portfolio + wait for updates
   - Show initial portfolio state
   ↓
6. Backend: Receive fill via WebSocket
   - Order executed on Kalshi
   - WebSocket message received
   - Update database with new position
   ↓
7. Backend: Push update to frontend
   - (Future: GraphQL subscription)
   - (Current: Frontend re-queries on interval or manual refresh)
   ↓
8. Frontend: Display updated portfolio
   - Show new position
   - Updated P&L
```

---

## Technology Stack Summary

### Backend
- **Language**: Python 3.11
- **Framework**: FastAPI
- **GraphQL**: Strawberry
- **Kalshi SDK**: `kalshi-python`
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy (async)

### Frontend
- **Language**: TypeScript
- **Framework**: React 18
- **Build Tool**: Vite
- **GraphQL Client**: Apollo Client
- **Kalshi SDK**: `kalshi-typescript`
- **UI Library**: shadcn/ui + Tailwind CSS

### Infrastructure (Phase 1)
- **Local Development**: Docker Compose
- **Database**: PostgreSQL 15
- **Caching**: None (Phase 2: Redis)

---

## Configuration Files

### backend/requirements.txt
```
fastapi>=0.104.0
strawberry-graphql[fastapi]>=0.200.0
kalshi-python>=1.0.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.28.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

### frontend/package.json
```json
{
  "dependencies": {
    "@apollo/client": "^3.8.0",
    "kalshi-typescript": "^1.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "graphql": "^16.8.0"
  }
}
```

### backend/.env.example
```bash
# Kalshi API Configuration
KALSHI_API_KEY_ID=your_key_id_here
KALSHI_PRIVATE_KEY_PATH=/path/to/private_key.pem
KALSHI_API_BASE=https://demo-api.kalshi.com

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/kalshi_db  # pragma: allowlist secret

# Security (future)
# JWT_SECRET=your_secret_key
# ENCRYPTION_KEY=your_encryption_key
```

### frontend/.env.example
```bash
# Kalshi TypeScript SDK (read-only)
VITE_KALSHI_READ_ONLY_KEY=your_read_only_api_key

# Backend API
VITE_API_URL=http://localhost:8000/graphql
```

---

## Next Steps

1. **Install SDKs**:
   ```bash
   # Backend
   cd backend
   pip install kalshi-python

   # Frontend
   cd frontend
   pnpm add kalshi-typescript
   ```

2. **Configure Authentication**:
   - Get Kalshi API credentials
   - Create backend `.env` with API key ID and private key path
   - Create frontend `.env.local` with read-only API key

3. **Implement Backend Service Layer**:
   - Create `backend/services/kalshi_service.py`
   - Initialize Kalshi Python SDK client
   - Implement order placement, portfolio fetching

4. **Build GraphQL Schema**:
   - Define types in `backend/api/schema.py`
   - Implement mutations for trading
   - Implement queries for portfolio

5. **Frontend Integration**:
   - Configure TypeScript SDK in `frontend/src/lib/kalshi.ts`
   - Build market browsing components
   - Implement order placement UI with backend mutations

6. **Testing**:
   - Test backend SDK with Kalshi demo API
   - Test frontend SDK market data display
   - Test order placement flow end-to-end
   - Verify error handling and staleness indicators

---

## Success Criteria (Phase 1 MVP)

- ✅ Users can browse available markets using TypeScript SDK
- ✅ **Real-time price updates via WebSocket** (push-based, immediate)
- ✅ **Order book depth charts** with live updates
- ✅ Users can place orders via backend Python SDK
- ✅ Portfolio displays current positions from backend
- ✅ **Fill notifications** pushed instantly when orders execute
- ✅ **Connection status indicators** (connected/reconnecting/failed)
- ✅ **Automatic reconnection** with exponential backoff
- ✅ Clear error messages on backend failures
- ✅ Orders and trades persist in PostgreSQL
- ✅ Graceful fallback to GraphQL when WebSocket fails

---

## Appendix: Key Architectural Decisions

### Decision 1: Why Hybrid Dual-SDK?
**Rationale**:
- Frontend SDK provides fast market browsing without backend load
- Backend SDK ensures secure trading operations and data persistence
- Separation of concerns: read-heavy vs. write-heavy operations

### Decision 2: Why WebSocket Subscriptions for Phase 1?
**Rationale**:
- Kalshi natively supports WebSockets with both SDKs
- Push-based updates are more efficient than polling
- Immediate price updates and order book changes
- Native fill notifications when orders execute
- Better user experience with real-time data
- No additional polling infrastructure needed

### Decision 3: Why Backend as Source of Truth?
**Rationale**:
- Trading operations must be authenticated and audited
- Portfolio state needs persistence and reconciliation
- Frontend SDK can fail; backend provides fallback
- Future multi-user support requires centralized state

### Decision 4: Why Staleness Indicators?
**Rationale**:
- Users need visibility when data is cached or outdated
- Maintains trust during SDK failures
- Informs trading decisions (don't trade on stale prices)
- Better UX than hard failures or silent errors
