/**
 * Market data hooks using Tanstack Query
 */
import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { marketsApi, type MarketSnapshot, type MarketSnapshotListResponse } from '@/api/markets'

interface UseMarketsParams {
  ticker: string
  skip?: number
  limit?: number
}

/**
 * Hook to fetch market snapshots with auto-refresh
 */
export function useMarkets({
  ticker,
  skip = 0,
  limit = 100,
}: UseMarketsParams): UseQueryResult<MarketSnapshotListResponse> {
  return useQuery({
    queryKey: ['markets', ticker, skip, limit],
    queryFn: () => marketsApi.getSnapshots(ticker, { skip, limit }),
    staleTime: 5_000, // 5s (matches backend polling interval)
    refetchInterval: 5_000, // Auto-refresh every 5s
    placeholderData: (previousData) => previousData, // Prevent loading jumps
  })
}

/**
 * Hook to fetch latest market snapshot
 */
export function useLatestMarket(ticker: string): UseQueryResult<MarketSnapshot> {
  return useQuery({
    queryKey: ['markets', ticker, 'latest'],
    queryFn: () => marketsApi.getLatest(ticker),
    staleTime: 5_000,
    refetchInterval: 5_000,
    placeholderData: (previousData) => previousData,
  })
}

/**
 * Hook to fetch market snapshot by ID
 */
export function useMarketById(id: string): UseQueryResult<MarketSnapshot> {
  return useQuery({
    queryKey: ['markets', id],
    queryFn: () => marketsApi.getById(id),
    enabled: !!id, // Only fetch if ID exists
  })
}
