# Frontend Architecture Documentation

**Project:** Kalshi Market Analytics - Frontend
**Phase:** 1 (Local Analytics Workbench)
**Version:** 0.1.0
**Last Updated:** 2025-10-03

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [Directory Structure](#directory-structure)
4. [Type System](#type-system)
5. [Data Fetching Strategy](#data-fetching-strategy)
6. [Component Architecture](#component-architecture)
7. [Routing & Navigation](#routing--navigation)
8. [State Management](#state-management)
9. [Styling & UI](#styling--ui)
10. [Phase Evolution](#phase-evolution)

---

## Overview

### Purpose

The Kalshi Analytics frontend is a **React + TypeScript** application designed for quantitative trading strategy visualization and analysis. It follows a **phased evolution** from simple data display (Phase 1) to real-time WebSocket updates (Phase 2) to multi-user platform (Phase 4).

### Core Objectives

- **Type Safety:** TypeScript throughout, mirroring backend Pydantic schemas
- **Data Synchronization:** Automatic refresh matching backend 5s polling
- **Clean Architecture:** Clear separation of data fetching, business logic, and UI
- **React Best Practices:** Hooks, composition, modern patterns
- **Portfolio Quality:** Polished UI with shadcn/ui and Tailwind CSS

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Build Tool** | Vite 5+ | Fast dev server, HMR, optimized builds |
| **Framework** | React 18+ | UI library with hooks and concurrent features |
| **Language** | TypeScript 5+ | Type safety and IDE support |
| **Data Fetching** | Tanstack Query v5 | Server state management, caching, polling |
| **HTTP Client** | Axios | Type-safe REST API calls |
| **Routing** | React Router v6 | Client-side navigation |
| **UI Components** | shadcn/ui | Accessible, customizable components |
| **Styling** | Tailwind CSS | Utility-first CSS framework |
| **Charts** | Recharts | React-based charting library |

---

## Architecture Principles

### 1. Feature-Based Organization

```
src/
├── api/           # API client layer
├── hooks/         # Data fetching hooks (Tanstack Query)
├── components/    # UI components (feature-based)
│   ├── markets/
│   └── backtests/
├── pages/         # Route components (composition)
└── types/         # TypeScript interfaces
```

**Benefits:**
- Easy to locate files by feature (markets, backtests)
- Clear separation: data (hooks) vs presentation (components)
- Scalable for new features (add new feature folder)

### 2. Type-Safe API Integration

**Backend Pydantic Schema:**
```python
class MarketResponse(BaseModel):
    ticker: str
    title: str
    yes_price: Decimal
    no_price: Decimal
    implied_probability: Decimal
    volume: int
    status: str
    last_updated: datetime
```

**Frontend TypeScript Type:**
```typescript
interface Market {
  ticker: string;
  title: string;
  yes_price: number;
  no_price: number;
  implied_probability: number;
  volume: number;
  status: 'active' | 'closed' | 'settled';
  last_updated: string;  // ISO datetime
}
```

**Benefits:**
- Single source of truth (backend defines schema)
- Compile-time type checking prevents runtime errors
- IDE autocomplete for API responses

### 3. Data Fetching Abstraction

**Component doesn't know about API:**
```typescript
// ❌ BAD: Component calls API directly
function MarketTable() {
  const [markets, setMarkets] = useState([]);

  useEffect(() => {
    fetch('/api/v1/markets').then(res => res.json()).then(setMarkets);
  }, []);
}

// ✅ GOOD: Component uses hook
function MarketTable() {
  const { data: markets, isLoading, error } = useMarkets();
  // Component only handles presentation
}
```

**Benefits:**
- Components focus on UI, not data fetching logic
- Easy to mock hooks for testing
- Phase 2 WebSocket migration: replace hook internals, components unchanged

### 4. Automatic Data Synchronization

**Tanstack Query matches backend polling:**
```typescript
export function useMarkets() {
  return useQuery({
    queryKey: ['markets'],
    queryFn: () => marketsApi.getAll(),
    staleTime: 5000,        // 5 seconds (matches backend poller)
    refetchInterval: 5000,  // Auto-refresh every 5s
  });
}
```

**Benefits:**
- UI always shows latest data (no manual refresh needed)
- Matches backend polling rate (no lag or duplication)
- Battery-efficient (no WebSocket overhead in Phase 1)

### 5. Composition Over Complexity

**Page components compose smaller pieces:**
```typescript
// pages/MarketsPage.tsx
export function MarketsPage() {
  return (
    <div>
      <PageHeader />
      <MarketFilters />
      <MarketTable />
    </div>
  );
}
```

**Benefits:**
- Easy to understand for React beginners
- Reusable components (use MarketTable elsewhere)
- Testable in isolation

---

## Directory Structure

### Complete Layout

```
frontend/
├── src/
│   ├── api/                      # API Client Layer
│   │   ├── client.ts             # Axios instance with config
│   │   ├── markets.ts            # Markets API calls
│   │   └── backtests.ts          # Backtests API calls
│   │
│   ├── components/               # UI Components
│   │   ├── ui/                   # shadcn/ui primitives (auto-generated)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── data-table.tsx
│   │   │   └── ...
│   │   ├── markets/              # Market feature components
│   │   │   ├── MarketTable.tsx   # Markets list with DataTable
│   │   │   ├── MarketDetail.tsx  # Market detail card
│   │   │   ├── PriceChart.tsx    # Recharts line chart
│   │   │   └── columns.tsx       # DataTable column definitions
│   │   └── backtests/            # Backtest feature components
│   │       ├── BacktestForm.tsx  # Strategy execution form
│   │       ├── BacktestResults.tsx # Results display
│   │       └── ReliabilityDiagram.tsx # Calibration chart
│   │
│   ├── hooks/                    # Tanstack Query Hooks
│   │   ├── useMarkets.ts         # Markets data fetching
│   │   ├── useMarket.ts          # Single market detail
│   │   ├── useMarketSnapshots.ts # Historical snapshots
│   │   ├── useBacktests.ts       # Backtest list
│   │   └── useCreateBacktest.ts  # Backtest execution
│   │
│   ├── types/                    # TypeScript Definitions
│   │   ├── market.ts             # Market, MarketSnapshot interfaces
│   │   └── backtest.ts           # BacktestRequest, BacktestResult
│   │
│   ├── lib/                      # Utilities
│   │   ├── utils.ts              # cn() for className merging
│   │   └── formatters.ts         # Date, number formatting
│   │
│   ├── pages/                    # Route Components
│   │   ├── MarketsPage.tsx       # /markets route
│   │   ├── MarketDetailPage.tsx  # /markets/:ticker route
│   │   └── BacktestsPage.tsx     # /backtests route
│   │
│   ├── App.tsx                   # Router setup, QueryClient provider
│   ├── main.tsx                  # Entry point (ReactDOM.render)
│   └── index.css                 # Tailwind imports, global styles
│
├── public/                       # Static assets
├── index.html                    # HTML template
├── package.json                  # Dependencies
├── tsconfig.json                 # TypeScript config
├── vite.config.ts                # Vite config
├── tailwind.config.js            # Tailwind config
├── components.json               # shadcn/ui config
├── .env.example                  # Environment variables template
└── README.md                     # Setup instructions
```

---

## Type System

### TypeScript Interfaces

**Matching Backend Pydantic Models:**

```typescript
// types/market.ts
export interface Market {
  ticker: string;
  title: string;
  yes_price: number;
  no_price: number;
  implied_probability: number;  // Backend calculates: yes_price / 100
  volume: number;
  status: 'active' | 'closed' | 'settled';
  last_updated: string;  // ISO 8601 datetime
}

export interface MarketSnapshot {
  ticker: string;
  timestamp: string;  // ISO 8601 datetime
  yes_price: number;
  no_price: number;
  volume: number;
}

// types/backtest.ts
export interface BacktestRequest {
  strategy: string;
  market_filter?: string;
  start_date: string;  // YYYY-MM-DD
  end_date: string;
}

export interface BacktestResult {
  id: string;
  strategy_name: string;
  start_date: string;
  end_date: string;
  total_pnl: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  num_trades: number;
  created_at: string;
}

export interface BacktestExecution {
  id: string;
  backtest_id: string;
  entry_time: string;
  exit_time: string | null;
  entry_price: number;
  exit_price: number | null;
  pnl: number;
  signal_metadata: Record<string, unknown>;
}
```

**Type Guards (Runtime Type Checking):**

```typescript
// lib/typeGuards.ts
export function isMarket(obj: unknown): obj is Market {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'ticker' in obj &&
    'yes_price' in obj
  );
}
```

---

## Data Fetching Strategy

### API Client Setup

```typescript
// api/client.ts
import axios from 'axios';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,  // 10 second timeout
});

// Global error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 429) {
      console.error('Rate limit exceeded');
    }
    return Promise.reject(error);
  }
);

export default apiClient;
```

### API Layer (Type-Safe Calls)

```typescript
// api/markets.ts
import apiClient from './client';
import type { Market, MarketSnapshot } from '@/types/market';

export const marketsApi = {
  /**
   * Fetch all markets with optional filtering
   */
  getAll: async (params?: {
    status?: string;
    limit?: number
  }): Promise<Market[]> => {
    const { data } = await apiClient.get<Market[]>('/api/v1/markets', { params });
    return data;
  },

  /**
   * Fetch single market by ticker
   */
  getByTicker: async (ticker: string): Promise<Market> => {
    const { data } = await apiClient.get<Market>(`/api/v1/markets/${ticker}`);
    return data;
  },

  /**
   * Fetch historical snapshots for backtesting
   */
  getSnapshots: async (
    ticker: string,
    startDate: string,
    endDate: string
  ): Promise<MarketSnapshot[]> => {
    const { data } = await apiClient.get<MarketSnapshot[]>(
      `/api/v1/markets/${ticker}/snapshots`,
      {
        params: {
          start_date: startDate,
          end_date: endDate
        }
      }
    );
    return data;
  },
};

// api/backtests.ts
import apiClient from './client';
import type { BacktestRequest, BacktestResult } from '@/types/backtest';

export const backtestsApi = {
  getAll: async (): Promise<BacktestResult[]> => {
    const { data } = await apiClient.get<BacktestResult[]>('/api/v1/backtests');
    return data;
  },

  getById: async (id: string): Promise<BacktestResult> => {
    const { data } = await apiClient.get<BacktestResult>(`/api/v1/backtests/${id}`);
    return data;
  },

  create: async (request: BacktestRequest): Promise<BacktestResult> => {
    const { data } = await apiClient.post<BacktestResult>('/api/v1/backtests', request);
    return data;
  },
};
```

### Tanstack Query Hooks

**Market Hooks:**

```typescript
// hooks/useMarkets.ts
import { useQuery } from '@tanstack/react-query';
import { marketsApi } from '@/api/markets';

export function useMarkets(status?: string, limit?: number) {
  return useQuery({
    queryKey: ['markets', status, limit],
    queryFn: () => marketsApi.getAll({ status, limit }),
    staleTime: 5000,        // Consider data stale after 5s
    refetchInterval: 5000,  // Auto-refresh every 5s (matches backend polling)
  });
}

export function useMarket(ticker: string) {
  return useQuery({
    queryKey: ['market', ticker],
    queryFn: () => marketsApi.getByTicker(ticker),
    staleTime: 5000,
    refetchInterval: 5000,
    enabled: !!ticker,  // Only fetch if ticker exists
  });
}

export function useMarketSnapshots(
  ticker: string,
  startDate: string,
  endDate: string
) {
  return useQuery({
    queryKey: ['market-snapshots', ticker, startDate, endDate],
    queryFn: () => marketsApi.getSnapshots(ticker, startDate, endDate),
    enabled: !!ticker && !!startDate && !!endDate,
    staleTime: Infinity,  // Historical data doesn't change
  });
}
```

**Backtest Hooks:**

```typescript
// hooks/useBacktests.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { backtestsApi } from '@/api/backtests';
import type { BacktestRequest } from '@/types/backtest';

export function useBacktests() {
  return useQuery({
    queryKey: ['backtests'],
    queryFn: () => backtestsApi.getAll(),
  });
}

export function useBacktest(id: string) {
  return useQuery({
    queryKey: ['backtest', id],
    queryFn: () => backtestsApi.getById(id),
    enabled: !!id,
  });
}

export function useCreateBacktest() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: BacktestRequest) => backtestsApi.create(request),
    onSuccess: () => {
      // Invalidate and refetch backtest list
      queryClient.invalidateQueries({ queryKey: ['backtests'] });
    },
  });
}
```

**Key Features:**
- Automatic caching and deduplication
- Background refetching (5s interval matches backend)
- Conditional fetching (`enabled` flag)
- Optimistic updates (mutation invalidation)
- Loading and error states built-in

---

## Component Architecture

### UI Component Hierarchy

```
App
├── MarketsPage
│   ├── PageHeader
│   ├── MarketFilters (future)
│   └── MarketTable
│       └── DataTable (shadcn/ui)
│           └── MarketRow (custom cells)
│
├── MarketDetailPage
│   ├── MarketDetailCard
│   │   ├── PriceDisplay
│   │   └── MetadataDisplay
│   └── PriceChart (Recharts)
│
└── BacktestsPage
    ├── BacktestForm
    │   └── Form (shadcn/ui)
    └── BacktestResults
        ├── MetricsCards
        └── ReliabilityDiagram
```

### Component Examples

**Market Table (Data Display):**

```typescript
// components/markets/MarketTable.tsx
import { useMarkets } from '@/hooks/useMarkets';
import { DataTable } from '@/components/ui/data-table';
import { columns } from './columns';

export function MarketTable() {
  const { data: markets, isLoading, error } = useMarkets('active');

  if (isLoading) {
    return <div className="text-center py-8">Loading markets...</div>;
  }

  if (error) {
    return (
      <div className="text-center py-8 text-destructive">
        Error loading markets. Please try again.
      </div>
    );
  }

  return (
    <DataTable
      columns={columns}
      data={markets || []}
      searchKey="title"
    />
  );
}

// components/markets/columns.tsx
import { ColumnDef } from '@tanstack/react-table';
import type { Market } from '@/types/market';
import { Badge } from '@/components/ui/badge';

export const columns: ColumnDef<Market>[] = [
  {
    accessorKey: 'ticker',
    header: 'Ticker',
  },
  {
    accessorKey: 'title',
    header: 'Title',
  },
  {
    accessorKey: 'yes_price',
    header: 'Yes Price',
    cell: ({ row }) => `$${row.getValue('yes_price')}`,
  },
  {
    accessorKey: 'implied_probability',
    header: 'Probability',
    cell: ({ row }) => `${(row.getValue('implied_probability') as number).toFixed(1)}%`,
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => {
      const status = row.getValue('status') as string;
      return (
        <Badge variant={status === 'active' ? 'default' : 'secondary'}>
          {status}
        </Badge>
      );
    },
  },
];
```

**Price Chart (Visualization):**

```typescript
// components/markets/PriceChart.tsx
import { useMarketSnapshots } from '@/hooks/useMarkets';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import { format } from 'date-fns';

interface PriceChartProps {
  ticker: string;
  startDate: string;
  endDate: string;
}

export function PriceChart({ ticker, startDate, endDate }: PriceChartProps) {
  const { data: snapshots, isLoading } = useMarketSnapshots(
    ticker,
    startDate,
    endDate
  );

  if (isLoading) {
    return <div className="h-96 flex items-center justify-center">Loading chart...</div>;
  }

  const chartData = snapshots?.map(s => ({
    timestamp: format(new Date(s.timestamp), 'MMM dd HH:mm'),
    yes: s.yes_price,
    no: s.no_price,
  })) || [];

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={chartData}>
        <XAxis
          dataKey="timestamp"
          tick={{ fontSize: 12 }}
          interval="preserveStartEnd"
        />
        <YAxis domain={[0, 100]} />
        <Tooltip />
        <Legend />
        <Line
          type="monotone"
          dataKey="yes"
          stroke="#10b981"
          name="Yes Price"
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="no"
          stroke="#ef4444"
          name="No Price"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

**Backtest Form (User Input):**

```typescript
// components/backtests/BacktestForm.tsx
import { useForm } from 'react-hook-form';
import { useCreateBacktest } from '@/hooks/useBacktests';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { BacktestRequest } from '@/types/backtest';

export function BacktestForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<BacktestRequest>();
  const createBacktest = useCreateBacktest();

  const onSubmit = (data: BacktestRequest) => {
    createBacktest.mutate(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <Label htmlFor="strategy">Strategy Name</Label>
        <Input
          id="strategy"
          {...register('strategy', { required: true })}
          placeholder="fade_overreaction"
        />
        {errors.strategy && <span className="text-sm text-destructive">Required</span>}
      </div>

      <div>
        <Label htmlFor="start_date">Start Date</Label>
        <Input
          id="start_date"
          type="date"
          {...register('start_date', { required: true })}
        />
      </div>

      <div>
        <Label htmlFor="end_date">End Date</Label>
        <Input
          id="end_date"
          type="date"
          {...register('end_date', { required: true })}
        />
      </div>

      <Button
        type="submit"
        disabled={createBacktest.isPending}
      >
        {createBacktest.isPending ? 'Running...' : 'Run Backtest'}
      </Button>
    </form>
  );
}
```

---

## Routing & Navigation

### Router Setup

```typescript
// App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import { MarketsPage } from '@/pages/MarketsPage';
import { MarketDetailPage } from '@/pages/MarketDetailPage';
import { BacktestsPage } from '@/pages/BacktestsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5000,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-background">
          <nav className="border-b">
            {/* Navigation bar here */}
          </nav>
          <main className="container mx-auto py-6">
            <Routes>
              <Route path="/" element={<Navigate to="/markets" replace />} />
              <Route path="/markets" element={<MarketsPage />} />
              <Route path="/markets/:ticker" element={<MarketDetailPage />} />
              <Route path="/backtests" element={<BacktestsPage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}

export default App;
```

### Page Components

**Markets List Page:**

```typescript
// pages/MarketsPage.tsx
import { MarketTable } from '@/components/markets/MarketTable';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

export function MarketsPage() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Kalshi Markets</h1>
        <Link to="/backtests">
          <Button>View Backtests</Button>
        </Link>
      </div>
      <MarketTable />
    </div>
  );
}
```

**Market Detail Page:**

```typescript
// pages/MarketDetailPage.tsx
import { useParams, Link } from 'react-router-dom';
import { useMarket } from '@/hooks/useMarkets';
import { PriceChart } from '@/components/markets/PriceChart';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ArrowLeft } from 'lucide-react';

export function MarketDetailPage() {
  const { ticker } = useParams<{ ticker: string }>();
  const { data: market, isLoading } = useMarket(ticker!);

  if (isLoading) {
    return <div>Loading market details...</div>;
  }

  if (!market) {
    return <div>Market not found</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/markets">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <h1 className="text-3xl font-bold">{market.title}</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Market Prices</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div>
              <p className="text-sm text-muted-foreground">Yes Price</p>
              <p className="text-2xl font-bold text-green-600">${market.yes_price}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">No Price</p>
              <p className="text-2xl font-bold text-red-600">${market.no_price}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Probability</p>
              <p className="text-2xl font-bold">{market.implied_probability.toFixed(1)}%</p>
            </div>
          </div>

          <PriceChart
            ticker={ticker!}
            startDate="2024-01-01"
            endDate="2024-12-31"
          />
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## State Management

### Server State (Tanstack Query)

**All API data managed by Tanstack Query:**
- Markets list
- Market details
- Historical snapshots
- Backtest results

**Benefits:**
- Automatic caching and deduplication
- Background synchronization
- Optimistic updates
- No manual state management needed

### Client State (React Hooks)

**Local UI state:**
```typescript
// Filter state
const [statusFilter, setStatusFilter] = useState<string>('active');

// Form state (react-hook-form)
const form = useForm<BacktestRequest>();

// Modal/dialog state
const [isOpen, setIsOpen] = useState(false);
```

**No Global State Library Needed in Phase 1:**
- Server state handled by Tanstack Query
- UI state is local to components
- Context API for theme (if needed)

---

## Styling & UI

### Tailwind CSS Configuration

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        // ... shadcn/ui theme colors
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
```

### shadcn/ui Components

**Install via CLI:**
```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card data-table input label
```

**Customizable components in `components/ui/`:**
- Accessible by default (ARIA attributes)
- Themeable with CSS variables
- Composition-friendly

---

## Phase Evolution

### Phase 1 → Phase 2 (WebSocket Integration)

**Changes Required:**

1. **New Hook:** Replace REST polling with WebSocket
```typescript
// hooks/useMarketsLive.ts (Phase 2)
export function useMarketsLive() {
  const [markets, setMarkets] = useState<Market[]>([]);

  useEffect(() => {
    const ws = new WebSocket(import.meta.env.VITE_WS_URL);

    ws.onmessage = (event) => {
      const update = JSON.parse(event.data);
      setMarkets(prev => updateMarkets(prev, update));
    };

    return () => ws.close();
  }, []);

  return { data: markets, isLoading: false };
}
```

2. **Component Update:** Swap hook, UI unchanged
```typescript
// MarketTable.tsx (Phase 2)
- const { data: markets } = useMarkets();
+ const { data: markets } = useMarketsLive();
```

**No Breaking Changes:**
- Components don't change (same interface)
- Types remain the same
- UI stays identical

### Phase 2 → Phase 3 (Authentication)

**Changes Required:**

1. **New Context:** Auth provider
```typescript
// contexts/AuthContext.tsx (Phase 3)
export function AuthProvider({ children }) {
  // Firebase Auth logic
}
```

2. **Protected Routes:**
```typescript
<Route element={<ProtectedRoute />}>
  <Route path="/backtests" element={<BacktestsPage />} />
</Route>
```

### Phase 3 → Phase 4 (GraphQL)

**Changes Required:**

1. **Apollo Client Setup:**
```typescript
// Phase 4: Add Apollo alongside Tanstack Query
const apolloClient = new ApolloClient({
  uri: import.meta.env.VITE_GRAPHQL_URL,
});
```

2. **GraphQL Hooks:**
```typescript
// hooks/useMarketsGraphQL.ts (Phase 4)
export function useMarketsGraphQL() {
  const { data } = useQuery(MARKETS_QUERY);
  return data?.markets || [];
}
```

**Backward Compatible:**
- REST endpoints remain available
- Can migrate routes incrementally
- Existing components work unchanged

---

## Configuration Files

### package.json

```json
{
  "name": "kalshi-analytics-frontend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "format": "prettier --write \"src/**/*.{ts,tsx}\""
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.14.0",
    "@tanstack/react-query-devtools": "^5.14.0",
    "axios": "^1.6.2",
    "recharts": "^2.10.3",
    "react-hook-form": "^7.49.2",
    "date-fns": "^3.0.0",
    "lucide-react": "^0.294.0",
    "@radix-ui/react-slot": "^1.0.2",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@typescript-eslint/eslint-plugin": "^6.14.0",
    "@typescript-eslint/parser": "^6.14.0",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.2.2",
    "vite": "^5.0.8",
    "eslint": "^8.55.0",
    "prettier": "^3.1.1",
    "tailwindcss": "^3.3.0",
    "postcss": "^8.4.32",
    "autoprefixer": "^10.4.16"
  }
}
```

### Environment Variables

**.env.example:**
```bash
# Backend API
VITE_API_URL=http://localhost:8000

# Phase 2+ (WebSocket)
# VITE_WS_URL=ws://localhost:8000/ws

# Phase 4+ (GraphQL)
# VITE_GRAPHQL_URL=http://localhost:8000/graphql
```

---

## Performance Optimization

### Code Splitting

```typescript
// Lazy load routes for better initial load
import { lazy, Suspense } from 'react';

const BacktestsPage = lazy(() => import('@/pages/BacktestsPage'));

<Route
  path="/backtests"
  element={
    <Suspense fallback={<div>Loading...</div>}>
      <BacktestsPage />
    </Suspense>
  }
/>
```

### Memoization

```typescript
// Expensive calculations
const chartData = useMemo(() =>
  snapshots?.map(s => ({
    timestamp: format(new Date(s.timestamp), 'MMM dd'),
    yes: s.yes_price,
  })),
  [snapshots]
);
```

### Virtual Scrolling (Future)

```typescript
// For large datasets (Phase 3+)
import { useVirtualizer } from '@tanstack/react-virtual';
```

---

## Testing Strategy

### Unit Tests (Vitest)

```typescript
// components/markets/MarketTable.test.tsx
import { render, screen } from '@testing-library/react';
import { MarketTable } from './MarketTable';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

describe('MarketTable', () => {
  it('displays markets', () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <MarketTable />
      </QueryClientProvider>
    );

    expect(screen.getByText('Loading markets...')).toBeInTheDocument();
  });
});
```

### E2E Tests (Playwright - Phase 2+)

```typescript
// e2e/markets.spec.ts
import { test, expect } from '@playwright/test';

test('displays market list', async ({ page }) => {
  await page.goto('/markets');
  await expect(page.locator('h1')).toContainText('Kalshi Markets');
  await expect(page.locator('table')).toBeVisible();
});
```

---

## Summary

This frontend architecture provides:

✅ **Type Safety:** TypeScript mirrors backend Pydantic schemas
✅ **Clean Architecture:** Feature-based organization, clear separation of concerns
✅ **Modern React:** Hooks, composition, Tanstack Query for server state
✅ **Auto Synchronization:** 5s polling matches backend, no manual refresh
✅ **Extensibility:** Ready for Phase 2 WebSocket and Phase 4 GraphQL
✅ **Portfolio Quality:** shadcn/ui + Tailwind for polished UI
✅ **Beginner-Friendly:** Clear patterns, well-organized, easy to navigate

**Total Implementation Time (Frontend):** 1 week alongside backend development

---

**Document Version:** 1.0
**Author:** System Design Agent
**Review Date:** 2025-10-03
