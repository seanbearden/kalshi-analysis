# Frontend Architecture Refinements

## Critical Improvements (Must Do Before Coding)

### 1. Auto-Generate TypeScript Types from OpenAPI

**Problem:** Manual type synchronization between Pydantic and TypeScript is error-prone.

**Solution:**
```bash
# Install
pnpm add -D openapi-typescript

# package.json script
"generate:types": "openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts"

# Usage
import type { components } from './types/api';
type Market = components['schemas']['MarketResponse'];
```

**Priority:** HIGH - Do this before writing any API code.

---

### 2. Enhanced API Client with Error Handling

```typescript
// api/client.ts
import axios, { AxiosError } from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
});

// Normalize FastAPI error responses
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail?: string }>) => {
    const message = error.response?.data?.detail || error.message;
    return Promise.reject(new Error(message));
  }
);

// Future auth (Phase 3)
apiClient.interceptors.request.use((config) => {
  // Will add: config.headers.Authorization = `Bearer ${token}`;
  return config;
});
```

---

### 3. Refined Tanstack Query Hooks

```typescript
// hooks/useMarkets.ts
import { useQuery, UseQueryOptions } from '@tanstack/react-query';

interface UseMarketsParams {
  status?: 'active' | 'settled' | 'all';
  search?: string;
  limit?: number;
  offset?: number;
}

export function useMarkets(
  params: UseMarketsParams = {},
  options?: UseQueryOptions<Market[], Error>
) {
  return useQuery({
    queryKey: ['markets', params], // Automatic cache segmentation
    queryFn: () => marketsApi.getMarkets(params),
    staleTime: 5_000,
    refetchInterval: 5_000,
    placeholderData: (previousData) => previousData, // Prevent loading jumps
    ...options,
  });
}

// Historical data - different refresh strategy
export function useMarketSnapshots(ticker: string, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['markets', ticker, 'snapshots', { startDate, endDate }],
    queryFn: () => marketsApi.getSnapshots(ticker, startDate, endDate),
    staleTime: 30_000, // Historical data doesn't change
    refetchInterval: false, // Don't auto-refresh
    enabled: !!ticker,
  });
}
```

---

### 4. Global Error Boundary

```typescript
// components/ErrorBoundary.tsx
import { Component, ErrorInfo, ReactNode } from 'react';

export class ErrorBoundary extends Component<{children: ReactNode}, {hasError: boolean, error?: Error}> {
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <h1>Something went wrong</h1>
            <p>{this.state.error?.message}</p>
            <Button onClick={() => this.setState({ hasError: false })}>
              Try again
            </Button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
```

---

### 5. Tanstack Query Global Configuration

```typescript
// lib/queryClient.ts
import { QueryClient, QueryCache, MutationCache } from '@tanstack/react-query';
import { toast } from '@/components/ui/use-toast';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5_000,
      refetchOnWindowFocus: true,
      refetchOnReconnect: true,
    },
    mutations: { retry: 0 },
  },
  queryCache: new QueryCache({
    onError: (error) => {
      toast({
        variant: 'destructive',
        title: 'Error',
        description: error.message,
      });
    },
  }),
  mutationCache: new MutationCache({
    onError: (error) => {
      toast({
        variant: 'destructive',
        title: 'Operation failed',
        description: error.message,
      });
    },
  }),
});
```

---

### 6. Form Validation with Zod

```typescript
// components/backtests/BacktestForm.tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const backtestSchema = z.object({
  strategy: z.enum(['long_favorite', 'mean_reversion', 'momentum']),
  start_date: z.string().datetime(),
  end_date: z.string().datetime(),
  initial_capital: z.number().min(100).max(1_000_000),
  max_position_size: z.number().min(0).max(1),
}).refine(
  (data) => new Date(data.end_date) > new Date(data.start_date),
  { message: 'End date must be after start date', path: ['end_date'] }
);

type BacktestFormData = z.infer<typeof backtestSchema>;

export function BacktestForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<BacktestFormData>({
    resolver: zodResolver(backtestSchema),
  });

  // ...
}
```

---

### 7. Environment Configuration Validation

```bash
# .env.example
VITE_API_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
VITE_ENABLE_WEBSOCKET=false
VITE_ENABLE_GRAPHQL=false
VITE_ENABLE_DEVTOOLS=true
```

```typescript
// config/env.ts
import { z } from 'zod';

const envSchema = z.object({
  VITE_API_URL: z.string().url(),
  VITE_API_TIMEOUT: z.coerce.number().default(30000),
  VITE_ENABLE_WEBSOCKET: z.coerce.boolean().default(false),
  VITE_ENABLE_GRAPHQL: z.coerce.boolean().default(false),
  VITE_ENABLE_DEVTOOLS: z.coerce.boolean().default(true),
});

export const env = envSchema.parse(import.meta.env);
```

---

## Phase 2 WebSocket Implementation Strategy

### Custom WebSocket Hook

```typescript
// hooks/useWebSocket.ts
export function useWebSocket<T>(url: string, queryKey: string[]) {
  const queryClient = useQueryClient();
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => setIsConnected(true);
    ws.onclose = () => setIsConnected(false);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data) as T;
      queryClient.setQueryData(queryKey, data);
    };

    return () => ws.close();
  }, [url, queryClient]);

  return { isConnected };
}

// Usage
export function useOrderbookLive(ticker: string) {
  const { isConnected } = useWebSocket<Orderbook>(
    `ws://localhost:8000/ws/orderbook/${ticker}`,
    ['orderbook', ticker]
  );

  return useQuery({
    queryKey: ['orderbook', ticker],
    queryFn: () => orderbookApi.get(ticker), // Fallback if WS disconnects
    enabled: !isConnected,
  });
}
```

---

## React Beginner Guidance

### Common Pitfalls to Avoid

**Pitfall 1: Re-fetching in every component**
```typescript
// ❌ BAD - Multiple fetches
function Page() {
  return (
    <>
      <MarketTable />  {/* Fetches markets */}
      <MarketChart />  {/* Fetches same markets again! */}
    </>
  );
}

// ✅ GOOD - Tanstack Query deduplicates automatically
// Both components use same queryKey ['markets'] - only one network request
```

**Pitfall 2: Not handling loading states**
```typescript
// ❌ BAD - Crash if data is undefined
function MarketTable() {
  const { data } = useMarkets();
  return <Table data={data} />; // Crashes during loading
}

// ✅ GOOD - Guard against undefined
function MarketTable() {
  const { data, isLoading } = useMarkets();

  if (isLoading) return <TableSkeleton />;
  if (!data) return <EmptyState />;

  return <Table data={data} />;
}
```

**Pitfall 3: Over-using useEffect**
```typescript
// ❌ BAD - Manual data fetching
function MarketDetail({ ticker }: Props) {
  const [market, setMarket] = useState();

  useEffect(() => {
    fetch(`/api/markets/${ticker}`)
      .then(r => r.json())
      .then(setMarket);
  }, [ticker]);
}

// ✅ GOOD - Let Tanstack Query handle it
function MarketDetail({ ticker }: Props) {
  const { data: market } = useMarket(ticker);
  return <div>{market?.yesPrice}</div>;
}
```

---

## Testing Strategy

### MSW Setup
```typescript
// tests/setup.ts
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

const mockMarkets = [
  { ticker: 'PREZ-2024', yes_price: 0.52, no_price: 0.48 },
];

export const server = setupServer(
  http.get('/api/markets', () => HttpResponse.json(mockMarkets))
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Component Test Example
```typescript
// components/markets/MarketTable.test.tsx
import { render, screen } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { MarketTable } from './MarketTable';

test('renders market data', async () => {
  render(
    <QueryClientProvider client={queryClient}>
      <MarketTable />
    </QueryClientProvider>
  );

  expect(await screen.findByText('PREZ-2024')).toBeInTheDocument();
});
```

---

## Accessibility Checklist

```typescript
// Add to MarketTable
<Table>
  <TableCaption>Real-time market data from Kalshi</TableCaption>
  <TableHeader>
    <TableRow>
      <TableHead scope="col">Ticker</TableHead>
    </TableRow>
  </TableHeader>
</Table>

// Keyboard navigation for chart
<PriceChart
  onKeyDown={(e) => {
    if (e.key === 'ArrowLeft') navigateToPreviousDataPoint();
  }}
  tabIndex={0}
  role="img"
  aria-label={`Price chart for ${ticker}`}
/>
```

**Install:** `pnpm add -D eslint-plugin-jsx-a11y`

---

## Development Experience Tooling

```json
// package.json scripts
{
  "dev": "vite",
  "build": "tsc && vite build",
  "lint": "eslint . --ext ts,tsx --max-warnings 0",
  "format": "prettier --write \"src/**/*.{ts,tsx}\"",
  "typecheck": "tsc --noEmit",
  "test": "vitest",
  "generate:types": "openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts"
}
```

---

## What NOT to Add (Phase 1)

**Skip these until later phases:**
- Redux/Zustand (React hooks + Tanstack Query is enough)
- Storybook (overkill for single-developer project)
- Micro-frontends (simple monolithic app)
- i18n (not a requirement)
- Feature flags service (use env vars)
- Advanced caching strategies (Tanstack Query defaults work)

---

## Implementation Build Order

### Week 1: Foundation
1. Project setup with type generation
2. Core infrastructure (api/client, queryClient, ErrorBoundary, env config)

### Week 2: Markets List
3. `useMarkets` hook
4. `MarketTable` component with shadcn/ui DataTable
5. `MarketsPage` route

### Week 3: Detail View + Charts
6. `useMarket` + `useMarketSnapshots` hooks
7. `PriceChart` with Recharts
8. `MarketDetailPage` route

### Week 4: Backtesting UI
9. `useBacktests` + `useCreateBacktest` hooks
10. `BacktestForm` with validation
11. `BacktestResults` display
12. `BacktestsPage` route
