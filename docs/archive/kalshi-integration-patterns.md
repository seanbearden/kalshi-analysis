# Kalshi Integration Patterns - Quick Reference

## Common WebSocket Patterns

### Pattern 1: Real-Time Market Price Display
**Use Case**: Show live prices for a single market

**Frontend (TypeScript)**:
```typescript
import { KalshiWebSocketClient } from 'kalshi-typescript';

const wsClient = new KalshiWebSocketClient({
  apiKey: import.meta.env.VITE_KALSHI_READ_ONLY_KEY
});

// Connect and subscribe
await wsClient.connect();
await wsClient.subscribe({
  type: 'ticker',
  market_ticker: 'INXD-24DEC31-B4500'
}, (message) => {
  console.log('Price update:', {
    yes: message.yes_price,
    no: message.no_price,
    volume: message.volume
  });
});
```

**When to Use**: Individual market pages, price tickers

---

### Pattern 2: Order Book Depth Visualization
**Use Case**: Display live order book with bids/asks

**Frontend (TypeScript)**:
```typescript
// Get initial snapshot
await wsClient.subscribe({
  type: 'orderbook_snapshot',
  market_ticker: 'INXD-24DEC31-B4500'
}, (snapshot) => {
  setOrderBook({
    yes_bids: snapshot.yes_bids,
    yes_asks: snapshot.yes_asks,
    no_bids: snapshot.no_bids,
    no_asks: snapshot.no_asks
  });
});

// Subscribe to deltas
await wsClient.subscribe({
  type: 'orderbook_update',
  market_ticker: 'INXD-24DEC31-B4500'
}, (delta) => {
  // Apply incremental update to existing order book
  applyOrderBookDelta(delta);
});
```

**When to Use**: Trading interfaces, depth charts, market analysis tools

---

### Pattern 3: Fill Notification Handling (Backend)
**Use Case**: Instantly update portfolio when orders execute

**Backend (Python)**:
```python
from kalshi_python import KalshiWebSocketClient

class FillNotificationService:
    def __init__(self):
        self.ws_client = KalshiWebSocketClient(
            api_key_id=os.getenv('KALSHI_API_KEY_ID'),
            private_key_path=os.getenv('KALSHI_PRIVATE_KEY_PATH')
        )

    async def subscribe_to_fills(self):
        async with self.ws_client.connect() as ws:
            # Authenticated channel - requires private key
            await ws.subscribe({'type': 'fills'})

            async for message in ws:
                if message['type'] == 'fill':
                    await self._process_fill(message)

    async def _process_fill(self, fill):
        # Update order status in database
        async with AsyncSessionLocal() as session:
            order = await session.get(Order, fill['order_id'])
            order.status = 'filled'

            # Create trade record
            trade = Trade(
                id=fill['fill_id'],
                order_id=fill['order_id'],
                fill_price=fill['price'],
                fill_quantity=fill['quantity']
            )
            session.add(trade)
            await session.commit()

            # Notify frontend (future: GraphQL subscription)
            print(f"Order {order.id} filled at ${fill['price']}")
```

**When to Use**: Portfolio tracking, order management, P&L calculation

---

### Pattern 4: Automatic Reconnection
**Use Case**: Maintain WebSocket connection despite network issues

**Frontend (TypeScript)**:
```typescript
async function connectWithRetry(wsClient: KalshiWebSocketClient, maxRetries = 5) {
  let retries = 0;

  while (retries < maxRetries) {
    try {
      await wsClient.connect();
      console.log('Connected to Kalshi WebSocket');
      retries = 0; // Reset on success
      return;

    } catch (error) {
      retries++;
      const delay = Math.min(1000 * Math.pow(2, retries), 30000); // Exponential backoff, max 30s

      console.warn(`Connection failed. Retry ${retries}/${maxRetries} in ${delay}ms`);

      if (retries >= maxRetries) {
        throw new Error('Max reconnection attempts reached');
      }

      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

// Usage
try {
  await connectWithRetry(wsClient);
  // Subscribe to channels after successful connection
} catch (error) {
  // Fallback to GraphQL polling
  console.error('WebSocket unavailable, using GraphQL fallback');
}
```

**When to Use**: All WebSocket connections for production reliability

---

### Pattern 5: Multi-Market Subscription
**Use Case**: Monitor prices for multiple markets simultaneously

**Frontend (TypeScript)**:
```typescript
const subscribeToMultipleMarkets = async (marketIds: string[]) => {
  const wsClient = new KalshiWebSocketClient({
    apiKey: import.meta.env.VITE_KALSHI_READ_ONLY_KEY
  });

  await wsClient.connect();

  for (const marketId of marketIds) {
    await wsClient.subscribe({
      type: 'ticker',
      market_ticker: marketId
    }, (message) => {
      // Update state for specific market
      updateMarketPrice(marketId, {
        yes: message.yes_price,
        no: message.no_price
      });
    });
  }

  return wsClient;
};

// Usage
const watchlist = ['MARKET-A', 'MARKET-B', 'MARKET-C'];
const wsClient = await subscribeToMultipleMarkets(watchlist);

// Cleanup on unmount
return () => wsClient.disconnect();
```

**When to Use**: Market dashboards, watchlists, portfolio monitoring

---

## GraphQL Patterns

### Pattern 6: Order Placement with Optimistic Updates
**Use Case**: Instant UI feedback when placing orders

**Frontend (TypeScript)**:
```typescript
import { useMutation } from '@apollo/client';
import { gql } from '@apollo/client';

const PLACE_ORDER = gql`
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

export function useOrderPlacement() {
  const [placeOrder, { loading, error }] = useMutation(PLACE_ORDER, {
    // Optimistic response for instant UI update
    optimisticResponse: (variables) => ({
      placeOrder: {
        __typename: 'Order',
        id: 'temp-' + Date.now(),
        marketId: variables.input.marketId,
        side: variables.input.side,
        quantity: variables.input.quantity,
        price: variables.input.price,
        status: 'pending'
      }
    }),
    // Update cache after mutation
    update: (cache, { data }) => {
      if (data?.placeOrder) {
        // Update order list in cache
        cache.modify({
          fields: {
            orders(existingOrders = []) {
              const newOrderRef = cache.writeFragment({
                data: data.placeOrder,
                fragment: gql`
                  fragment NewOrder on Order {
                    id
                    marketId
                    side
                    quantity
                    price
                    status
                  }
                `
              });
              return [...existingOrders, newOrderRef];
            }
          }
        });
      }
    }
  });

  return { placeOrder, loading, error };
}
```

**When to Use**: Trading forms, quick order execution

---

### Pattern 7: Portfolio Fetching with Caching
**Use Case**: Efficiently fetch portfolio with stale-while-revalidate

**Frontend (TypeScript)**:
```typescript
import { useQuery } from '@apollo/client';
import { gql } from '@apollo/client';

const GET_PORTFOLIO = gql`
  query GetPortfolio {
    portfolio {
      totalValue
      positions {
        marketId
        marketTitle
        quantity
        entryPrice
        currentPrice
        unrealizedPnl
      }
      isStale
      lastUpdated
    }
  }
`;

export function usePortfolio() {
  const { data, loading, error, refetch } = useQuery(GET_PORTFOLIO, {
    // Cache for 30 seconds
    pollInterval: 30000,
    // Use cached data while fetching new
    fetchPolicy: 'cache-and-network',
    // Return partial data if available
    returnPartialData: true
  });

  return {
    portfolio: data?.portfolio,
    isStale: data?.portfolio?.isStale ?? false,
    loading,
    error,
    refresh: refetch
  };
}
```

**When to Use**: Portfolio pages, position tracking

---

## Hybrid Patterns (REST + WebSocket)

### Pattern 8: Initial Load + Real-Time Updates
**Use Case**: Fast initial render with subsequent live updates

**Frontend (TypeScript)**:
```typescript
import { useState, useEffect } from 'react';
import { kalshiClient, KalshiWebSocketClient } from '../lib/kalshi';

export function useMarketWithLivePrice(marketId: string) {
  const [market, setMarket] = useState(null);
  const [livePrice, setLivePrice] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Initial fetch via REST
    const fetchMarket = async () => {
      const data = await kalshiClient.getMarket(marketId);
      setMarket(data);
      setLivePrice({ yes: data.yes_price, no: data.no_price });
      setLoading(false);
    };

    fetchMarket();

    // 2. Upgrade to WebSocket for live updates
    const wsClient = new KalshiWebSocketClient({
      apiKey: import.meta.env.VITE_KALSHI_READ_ONLY_KEY
    });

    const subscribeToPrices = async () => {
      await wsClient.connect();
      await wsClient.subscribe({
        type: 'ticker',
        market_ticker: marketId
      }, (message) => {
        setLivePrice({
          yes: message.yes_price,
          no: message.no_price
        });
      });
    };

    subscribeToPrices();

    return () => {
      wsClient.disconnect();
    };
  }, [marketId]);

  return { market, livePrice, loading };
}
```

**When to Use**: Market detail pages, dashboard tiles

---

### Pattern 9: Fallback on WebSocket Failure
**Use Case**: Graceful degradation to GraphQL when WebSocket fails

**Frontend (TypeScript)**:
```typescript
import { useState, useEffect } from 'react';
import { apolloClient } from '../lib/apollo';
import { gql } from '@apollo/client';

const GET_MARKET_PRICE = gql`
  query GetMarketPrice($id: ID!) {
    market(id: $id) {
      yesPrice
      noPrice
    }
  }
`;

export function useResilientMarketPrice(marketId: string) {
  const [price, setPrice] = useState(null);
  const [source, setSource] = useState<'websocket' | 'graphql'>('websocket');

  useEffect(() => {
    const wsClient = new KalshiWebSocketClient({
      apiKey: import.meta.env.VITE_KALSHI_READ_ONLY_KEY
    });

    const tryWebSocket = async () => {
      try {
        await wsClient.connect();
        setSource('websocket');

        await wsClient.subscribe({
          type: 'ticker',
          market_ticker: marketId
        }, (message) => {
          setPrice({ yes: message.yes_price, no: message.no_price });
        });

      } catch (error) {
        console.warn('WebSocket failed, falling back to GraphQL');
        fallbackToGraphQL();
      }
    };

    const fallbackToGraphQL = () => {
      setSource('graphql');

      // Poll via GraphQL instead
      const interval = setInterval(async () => {
        const { data } = await apolloClient.query({
          query: GET_MARKET_PRICE,
          variables: { id: marketId }
        });

        setPrice({
          yes: data.market.yesPrice,
          no: data.market.noPrice
        });
      }, 5000); // Poll every 5 seconds

      return () => clearInterval(interval);
    };

    tryWebSocket();

    return () => {
      wsClient.disconnect();
    };
  }, [marketId]);

  return { price, source };
}
```

**When to Use**: Production apps requiring high reliability

---

## Error Handling Patterns

### Pattern 10: Structured Error Handling
**Use Case**: Consistent error handling across WebSocket and GraphQL

**Frontend (TypeScript)**:
```typescript
type KalshiError = {
  code: string;
  message: string;
  retryable: boolean;
};

export function handleKalshiError(error: any): KalshiError {
  // WebSocket errors
  if (error.code) {
    const retryableCodes = ['connection_lost', 'timeout', 'rate_limit'];
    return {
      code: error.code,
      message: error.message || 'WebSocket error occurred',
      retryable: retryableCodes.includes(error.code)
    };
  }

  // GraphQL errors
  if (error.graphQLErrors?.length > 0) {
    const gqlError = error.graphQLErrors[0];
    return {
      code: gqlError.extensions?.code || 'UNKNOWN',
      message: gqlError.message,
      retryable: gqlError.extensions?.code === 'KALSHI_UNAVAILABLE'
    };
  }

  // Network errors
  if (error.networkError) {
    return {
      code: 'NETWORK_ERROR',
      message: 'Network connection failed',
      retryable: true
    };
  }

  // Unknown errors
  return {
    code: 'UNKNOWN_ERROR',
    message: error.message || 'An unexpected error occurred',
    retryable: false
  };
}

// Usage
try {
  await wsClient.connect();
} catch (error) {
  const kalshiError = handleKalshiError(error);

  if (kalshiError.retryable) {
    // Retry with backoff
    setTimeout(() => wsClient.connect(), 2000);
  } else {
    // Show error to user
    toast.error(kalshiError.message);
  }
}
```

**When to Use**: All production error handling

---

## Testing Patterns

### Pattern 11: Mock WebSocket for Testing
**Use Case**: Test WebSocket logic without real connections

**Frontend (Vitest)**:
```typescript
import { vi } from 'vitest';
import { KalshiWebSocketClient } from 'kalshi-typescript';

class MockKalshiWebSocket extends KalshiWebSocketClient {
  private mockMessages: any[] = [];

  async connect() {
    // Simulate connection
    return Promise.resolve();
  }

  async subscribe(channel: any, callback: Function) {
    // Simulate subscription
    this.mockMessages.forEach(msg => callback(msg));
  }

  // Test helper
  simulateMessage(message: any) {
    this.mockMessages.push(message);
  }
}

// Test
describe('useKalshiWebSocket', () => {
  it('updates price on ticker message', async () => {
    const mockWs = new MockKalshiWebSocket({ apiKey: 'test' });  // pragma: allowlist secret

    const { result } = renderHook(() => useKalshiWebSocket('MARKET-ID'));

    // Simulate price update
    mockWs.simulateMessage({
      type: 'ticker',
      yes_price: 50,
      no_price: 50
    });

    expect(result.current.price).toEqual({ yes: 50, no: 50 });
  });
});
```

**When to Use**: Unit and integration tests

---

## Performance Patterns

### Pattern 12: Subscription Pooling
**Use Case**: Share WebSocket connections across components

**Frontend (TypeScript)**:
```typescript
class WebSocketPool {
  private connections: Map<string, KalshiWebSocketClient> = new Map();
  private subscriptions: Map<string, Set<Function>> = new Map();

  async subscribe(marketId: string, callback: Function) {
    // Reuse existing connection
    if (!this.connections.has(marketId)) {
      const wsClient = new KalshiWebSocketClient({
        apiKey: import.meta.env.VITE_KALSHI_READ_ONLY_KEY
      });

      await wsClient.connect();
      await wsClient.subscribe({
        type: 'ticker',
        market_ticker: marketId
      }, (message) => {
        // Notify all subscribers
        const callbacks = this.subscriptions.get(marketId) || new Set();
        callbacks.forEach(cb => cb(message));
      });

      this.connections.set(marketId, wsClient);
      this.subscriptions.set(marketId, new Set());
    }

    // Add callback to subscription list
    this.subscriptions.get(marketId)!.add(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.subscriptions.get(marketId);
      callbacks?.delete(callback);

      // Close connection if no more subscribers
      if (callbacks?.size === 0) {
        this.connections.get(marketId)?.disconnect();
        this.connections.delete(marketId);
        this.subscriptions.delete(marketId);
      }
    };
  }
}

// Singleton instance
export const wsPool = new WebSocketPool();

// Usage in components
const unsubscribe = await wsPool.subscribe(marketId, (message) => {
  setPrice({ yes: message.yes_price, no: message.no_price });
});

// Cleanup
useEffect(() => {
  return () => unsubscribe();
}, []);
```

**When to Use**: Apps with many concurrent subscriptions

---

## Security Patterns

### Pattern 13: Credential Management (Backend Only)
**Use Case**: Never expose private keys to frontend

**Backend (Python)**:
```python
# ❌ NEVER DO THIS
# Exposing credentials to frontend
@strawberry.type
class Query:
    @strawberry.field
    async def get_kalshi_credentials(self) -> dict:
        return {
            'api_key_id': os.getenv('KALSHI_API_KEY_ID'),
            'private_key': os.getenv('KALSHI_PRIVATE_KEY')  # DANGER!
        }

# ✅ CORRECT APPROACH
# Backend proxies all authenticated operations
@strawberry.type
class Mutation:
    @strawberry.mutation
    async def place_order(
        self,
        input: OrderInput,
        info: Info
    ) -> Order:
        # Backend handles auth internally
        client = get_authenticated_kalshi_client()
        order = await client.place_order(
            ticker=input.market_id,
            side=input.side,
            quantity=input.quantity,
            price=input.price
        )
        return Order(**order)
```

**Frontend (TypeScript)**:
```typescript
// ✅ Frontend only uses read-only API key for market data
const wsClient = new KalshiWebSocketClient({
  apiKey: import.meta.env.VITE_KALSHI_READ_ONLY_KEY  // Public, read-only
});

// ❌ Never include private keys in frontend
// const wsClient = new KalshiWebSocketClient({
//   apiKey: 'key_id',  // pragma: allowlist secret
//   privateKey: 'private_key_content'  // DANGER!  // pragma: allowlist secret
// });
```

**When to Use**: Always! Never expose credentials to frontend

---

## Summary of Pattern Usage

| Pattern | Frontend/Backend | Use Case | Complexity |
|---------|------------------|----------|------------|
| 1. Real-Time Prices | Frontend | Market display | Low |
| 2. Order Book Depth | Frontend | Trading interface | Medium |
| 3. Fill Notifications | Backend | Portfolio updates | Medium |
| 4. Auto Reconnection | Both | Production reliability | Medium |
| 5. Multi-Market Sub | Frontend | Dashboards | Medium |
| 6. Optimistic Updates | Frontend | Fast UI | High |
| 7. Portfolio Caching | Frontend | Efficient loading | Low |
| 8. Initial + Live | Frontend | Fast + real-time | Medium |
| 9. WebSocket Fallback | Frontend | High reliability | High |
| 10. Error Handling | Both | Production quality | Medium |
| 11. Mock WebSocket | Testing | Unit tests | Low |
| 12. Subscription Pool | Frontend | Performance | High |
| 13. Credential Security | Backend | Security | Critical |

---

## Anti-Patterns (Avoid These!)

### ❌ Anti-Pattern 1: Polling When WebSocket Available
```typescript
// DON'T DO THIS
setInterval(async () => {
  const price = await kalshiClient.getMarket(marketId);
  setPrice(price);
}, 1000); // Wasteful polling every second
```

**Why Bad**: Wastes API calls, higher latency, no real-time benefits

**Solution**: Use WebSocket subscriptions (Pattern 1)

---

### ❌ Anti-Pattern 2: No Reconnection Logic
```typescript
// DON'T DO THIS
const wsClient = new KalshiWebSocketClient({ apiKey: 'key' });  // pragma: allowlist secret
await wsClient.connect(); // What if this fails?
```

**Why Bad**: Production apps fail on network issues

**Solution**: Always implement reconnection (Pattern 4)

---

### ❌ Anti-Pattern 3: Subscription Memory Leak
```typescript
// DON'T DO THIS
useEffect(() => {
  wsClient.subscribe({ type: 'ticker', market_ticker: marketId }, callback);
  // No cleanup!
}, [marketId]);
```

**Why Bad**: Leaks connections and memory

**Solution**: Always return cleanup function:
```typescript
useEffect(() => {
  const unsubscribe = wsClient.subscribe(...);
  return () => unsubscribe();
}, [marketId]);
```

---

### ❌ Anti-Pattern 4: Exposing Credentials to Frontend
```typescript
// DON'T DO THIS
const wsClient = new KalshiWebSocketClient({
  apiKey: 'key_id',  // pragma: allowlist secret
  privateKey: readFileSync('/path/to/private_key.pem')
});
```

**Why Bad**: Massive security vulnerability

**Solution**: Backend-only authentication (Pattern 13)

---

## Quick Decision Tree

**Need to display market prices?**
- Real-time required? → WebSocket (Pattern 1)
- Initial load only? → REST API

**Need to place orders?**
- Always use backend GraphQL mutation (Pattern 6)
- Never direct from frontend

**Need portfolio data?**
- Initial fetch → GraphQL query (Pattern 7)
- Live updates → WebSocket fills (Pattern 3)

**WebSocket disconnected?**
- Reconnect automatically (Pattern 4)
- Fallback to GraphQL (Pattern 9)

**Multiple markets to monitor?**
- Few markets → Individual subscriptions (Pattern 1)
- Many markets → Subscription pool (Pattern 12)

**Production deployment?**
- Must have: Patterns 4, 9, 10, 13
- Nice to have: Patterns 7, 12
