/**
 * Backtest hooks using Tanstack Query
 */
import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
  type UseMutationResult,
} from '@tanstack/react-query'
import {
  backtestsApi,
  type BacktestResult,
  type BacktestResultListResponse,
  type BacktestCreateRequest,
  type BacktestQueryParams,
} from '@/api/backtests'

/**
 * Hook to list backtests with optional filtering
 */
export function useBacktests(
  params?: BacktestQueryParams
): UseQueryResult<BacktestResultListResponse> {
  return useQuery({
    queryKey: ['backtests', params],
    queryFn: () => backtestsApi.list(params),
    staleTime: 30_000, // 30s for backtest results
  })
}

/**
 * Hook to fetch backtest by ID
 */
export function useBacktestById(
  id: string,
  includeExecutions = false
): UseQueryResult<BacktestResult> {
  return useQuery({
    queryKey: ['backtests', id, includeExecutions],
    queryFn: () => backtestsApi.getById(id, includeExecutions),
    enabled: !!id,
  })
}

/**
 * Hook to create new backtest
 */
export function useCreateBacktest(): UseMutationResult<
  BacktestResult,
  Error,
  BacktestCreateRequest
> {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (request: BacktestCreateRequest) => backtestsApi.create(request),
    onSuccess: () => {
      // Invalidate backtests list to trigger refetch
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
    },
  })
}
