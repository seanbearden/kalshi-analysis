# Frontend Architecture Summary

## Technology Stack (Phase 1)

**Core:**
- React 18+ with TypeScript 5+
- Vite 5+ for build tooling
- Tanstack Query v5 for server state (NOT Apollo/GraphQL in Phase 1)
- Axios for HTTP client
- React Router v6 for routing

**UI & Styling:**
- shadcn/ui component library
- Tailwind CSS for styling
- Recharts for data visualization
- Lucide icons

## Directory Structure

```
frontend/src/
├── api/              # API client layer (axios)
│   ├── client.ts
│   ├── markets.ts
│   └── backtests.ts
├── hooks/            # Tanstack Query hooks
│   ├── useMarkets.ts
│   ├── useMarket.ts
│   └── useBacktests.ts
├── components/       # Feature-based UI components
│   ├── ui/          # shadcn/ui auto-generated
│   ├── markets/
│   └── backtests/
├── pages/            # Route components
│   ├── MarketsPage.tsx
│   ├── MarketDetailPage.tsx
│   └── BacktestsPage.tsx
├── types/            # TypeScript interfaces (mirror backend)
│   ├── market.ts
│   └── backtest.ts
└── lib/              # Utilities
    └── utils.ts
```

## Key Design Patterns

### 1. Type-Safe API Integration
TypeScript interfaces mirror backend Pydantic schemas exactly:

```typescript
// Backend Pydantic
class MarketResponse(BaseModel):
    ticker: str
    yes_price: Decimal

// Frontend TypeScript
interface Market {
  ticker: string;
  yes_price: number;
}
```

### 2. Data Fetching Abstraction
Components use hooks, don't call API directly:

```typescript
// ✅ GOOD: Component uses hook
function MarketTable() {
  const { data: markets, isLoading } = useMarkets();
  // Only handles presentation
}

// ❌ BAD: Component calls API
function MarketTable() {
  const [markets, setMarkets] = useState([]);
  useEffect(() => {
    fetch('/api/markets').then(/* ... */);
  }, []);
}
```

### 3. Automatic Synchronization
Tanstack Query matches backend 5s polling:

```typescript
export function useMarkets() {
  return useQuery({
    queryKey: ['markets'],
    queryFn: () => marketsApi.getAll(),
    staleTime: 5000,        // 5s (matches backend)
    refetchInterval: 5000,  // Auto-refresh
  });
}
```

## Core Components

### MarketTable
- Uses shadcn/ui DataTable
- Auto-refreshing (5s interval)
- Column definitions for ticker, title, prices, status

### PriceChart
- Recharts LineChart
- Historical snapshots from backend
- Yes/No price lines with color coding

### BacktestForm
- react-hook-form for validation
- Mutation hook for API submission
- Automatic cache invalidation on success

## Routing

```typescript
Routes:
  /                    → Redirect to /markets
  /markets             → MarketsPage (table view)
  /markets/:ticker     → MarketDetailPage (detail + chart)
  /backtests           → BacktestsPage (form + results)
```

## State Management

**Server State:** Tanstack Query (markets, backtests)
**Client State:** React hooks (filters, forms, UI state)
**No Redux/Zustand needed in Phase 1**

## Phase 2 Migration Path (WebSocket)

Replace REST hook with WebSocket hook:

```typescript
// Phase 1: REST polling
const { data: markets } = useMarkets();

// Phase 2: WebSocket
const { data: markets } = useMarketsLive();

// Components unchanged!
```

## Environment Variables

```bash
# .env
VITE_API_URL=http://localhost:8000

# Phase 2+
# VITE_WS_URL=ws://localhost:8000/ws

# Phase 4+
# VITE_GRAPHQL_URL=http://localhost:8000/graphql
```

## Dependencies

**Production:**
- react, react-dom, react-router-dom
- @tanstack/react-query
- axios
- recharts
- react-hook-form
- shadcn/ui components
- tailwindcss

**Development:**
- vite
- typescript
- eslint, prettier
- @types/react, @types/react-dom

## Implementation Timeline

**Week 1 (Parallel with Backend):**
1. Day 1: Vite + TypeScript setup, shadcn/ui init
2. Day 2: API client + types
3. Day 3: Tanstack Query hooks
4. Day 4: MarketTable component
5. Day 5: MarketDetail + PriceChart
6. Day 6-7: BacktestForm + Results

**Total:** 1 week for Phase 1 frontend
