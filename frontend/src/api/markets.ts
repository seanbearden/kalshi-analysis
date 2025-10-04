/**
 * Markets API endpoints
 */
import { apiClient } from './client'

export interface MarketSnapshot {
  id: string
  ticker: string
  timestamp: string
  source: 'POLL' | 'WEBSOCKET' | 'BACKFILL'
  sequence: number | null
  yes_price: number
  no_price: number
  volume: number
  created_at: string
}

export interface MarketSnapshotListResponse {
  snapshots: MarketSnapshot[]
  total: number
  skip: number
  limit: number
}

export interface MarketQueryParams {
  skip?: number
  limit?: number
}

export const marketsApi = {
  /**
   * Get latest snapshot for all markets
   */
  getAllMarkets: async (params?: MarketQueryParams): Promise<MarketSnapshotListResponse> => {
    const { data } = await apiClient.get('/api/v1/markets', { params })
    return data
  },

  /**
   * Get all snapshots for a ticker
   */
  getSnapshots: async (
    ticker: string,
    params?: MarketQueryParams
  ): Promise<MarketSnapshotListResponse> => {
    const { data } = await apiClient.get(`/api/v1/markets/${ticker}/snapshots`, { params })
    return data
  },

  /**
   * Get latest snapshot for a ticker
   */
  getLatest: async (ticker: string): Promise<MarketSnapshot> => {
    const { data } = await apiClient.get(`/api/v1/markets/${ticker}/latest`)
    return data
  },

  /**
   * Get snapshot by ID
   */
  getById: async (id: string): Promise<MarketSnapshot> => {
    const { data } = await apiClient.get(`/api/v1/markets/${id}`)
    return data
  },
}
