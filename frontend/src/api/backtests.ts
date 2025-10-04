/**
 * Backtests API endpoints
 */
import { apiClient } from './client'

export type StrategyType = 'LONG_FAVORITE' | 'FADE_OVERREACTION' | 'MEAN_REVERSION' | 'MOMENTUM'
export type TradeDirection = 'LONG' | 'SHORT'

export interface BacktestExecution {
  id: string
  ticker: string
  direction: TradeDirection
  entry_time: string
  entry_price: number
  exit_time: string
  exit_price: number
  size: number
  pnl: number
  reason: string | null
}

export interface BacktestResult {
  id: string
  strategy: StrategyType
  start_date: string
  end_date: string
  market_filter: string | null
  total_pnl: number
  sharpe_ratio: number | null
  max_drawdown: number | null
  win_rate: number | null
  total_trades: number
  parameters: Record<string, unknown>
  created_at: string
  executions?: BacktestExecution[]
}

export interface BacktestResultListResponse {
  results: BacktestResult[]
  total: number
  skip: number
  limit: number
}

export interface BacktestCreateRequest {
  strategy: StrategyType
  start_date: string
  end_date: string
  market_filter?: string
  parameters?: Record<string, unknown>
}

export interface BacktestQueryParams {
  strategy?: StrategyType
  include_executions?: boolean
  skip?: number
  limit?: number
}

export const backtestsApi = {
  /**
   * List all backtests with optional filtering
   */
  list: async (params?: BacktestQueryParams): Promise<BacktestResultListResponse> => {
    const { data } = await apiClient.get('/api/v1/backtests/', { params })
    return data
  },

  /**
   * Get backtest by ID
   */
  getById: async (id: string, includeExecutions = false): Promise<BacktestResult> => {
    const { data } = await apiClient.get(`/api/v1/backtests/${id}`, {
      params: { include_executions: includeExecutions },
    })
    return data
  },

  /**
   * Create new backtest
   */
  create: async (request: BacktestCreateRequest): Promise<BacktestResult> => {
    const { data } = await apiClient.post('/api/v1/backtests/', request)
    return data
  },
}
