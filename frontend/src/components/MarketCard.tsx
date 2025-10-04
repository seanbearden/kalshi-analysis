import { motion } from 'framer-motion'
import type { MarketSnapshot } from '@/api/markets'

interface MarketCardProps {
  market: MarketSnapshot
  index: number
}

export function MarketCard({ market, index }: MarketCardProps) {
  const yesPrice = market.yes_price || 0
  const noPrice = market.no_price || 0
  const impliedProb = yesPrice / 100

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      whileHover={{ y: -4, transition: { duration: 0.2 } }}
      className="group relative rounded-lg border bg-card p-6 shadow-sm hover:shadow-md transition-shadow"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <code className="text-sm font-mono font-semibold text-foreground">{market.ticker}</code>
          <div className="mt-1 flex items-center gap-2">
            <span
              className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                market.source === 'POLL'
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                  : market.source === 'WEBSOCKET'
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
              }`}
            >
              {market.source}
            </span>
            <span className="text-xs text-muted-foreground">
              {new Date(market.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>

        {/* Implied Probability Badge */}
        <div className="text-right">
          <div className="text-2xl font-bold">{(impliedProb * 100).toFixed(0)}%</div>
          <div className="text-xs text-muted-foreground">probability</div>
        </div>
      </div>

      {/* Price Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="rounded-md bg-green-50 dark:bg-green-950/20 p-3">
          <div className="text-xs font-medium text-green-700 dark:text-green-400 mb-1">YES</div>
          <div className="text-xl font-bold text-green-900 dark:text-green-300">¢{yesPrice}</div>
        </div>

        <div className="rounded-md bg-red-50 dark:bg-red-950/20 p-3">
          <div className="text-xs font-medium text-red-700 dark:text-red-400 mb-1">NO</div>
          <div className="text-xl font-bold text-red-900 dark:text-red-300">¢{noPrice}</div>
        </div>
      </div>

      {/* Volume */}
      {market.volume !== null && market.volume !== undefined && (
        <div className="pt-3 border-t">
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">24h Volume</span>
            <span className="text-sm font-semibold">
              {market.volume.toLocaleString()} contracts
            </span>
          </div>
        </div>
      )}

      {/* Hover effect overlay */}
      <div className="absolute inset-0 rounded-lg bg-primary/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
    </motion.div>
  )
}
