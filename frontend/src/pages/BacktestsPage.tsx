import { useBacktests } from '../hooks/useBacktests'
import { format } from 'date-fns'
import { motion } from 'framer-motion'
import { BacktestCardSkeleton } from '../components/ui/Skeleton'

export default function BacktestsPage() {
  const { data, isLoading, error } = useBacktests()
  const backtests = data?.results || []

  if (isLoading) {
    return (
      <div>
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Backtests</h1>
          <p className="mt-2 text-muted-foreground">
            Strategy backtesting results and performance metrics
          </p>
        </div>
        <div className="grid gap-4">
          {[...Array(3)].map((_, i) => (
            <BacktestCardSkeleton key={i} />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
        <h3 className="font-semibold text-destructive">Error Loading Backtests</h3>
        <p className="mt-2 text-sm text-destructive/80">
          {error instanceof Error ? error.message : 'An unknown error occurred'}
        </p>
        <p className="mt-2 text-sm text-muted-foreground">
          Make sure the backend API is running on{' '}
          <code className="rounded bg-muted px-1 py-0.5">
            {import.meta.env.VITE_API_URL || 'http://localhost:8000'}
          </code>
        </p>
      </div>
    )
  }

  if (!backtests || backtests.length === 0) {
    return (
      <div>
        <div className="mb-6">
          <h1 className="text-3xl font-bold">Backtests</h1>
          <p className="mt-2 text-muted-foreground">
            Strategy backtesting results and performance metrics
          </p>
        </div>

        <div className="rounded-lg border bg-card p-8 text-center">
          <h3 className="text-lg font-semibold">No Backtests Yet</h3>
          <p className="mt-2 text-muted-foreground">
            Backtesting strategies will appear here once you run your first backtest
          </p>
          <p className="mt-4 text-sm text-muted-foreground">
            Phase 1 focuses on setting up the infrastructure. Strategy development happens in
            Jupyter notebooks.
          </p>
        </div>
      </div>
    )
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Backtests</h1>
        <p className="mt-2 text-muted-foreground">
          Strategy backtesting results and performance metrics
        </p>
      </div>

      <div className="grid gap-4">
        {backtests.map((backtest, index) => (
          <motion.div
            key={backtest.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1, duration: 0.3 }}
            whileHover={{ scale: 1.01, transition: { duration: 0.2 } }}
            className="rounded-lg border bg-card p-6 shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold">{backtest.strategy.replace('_', ' ')}</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {format(new Date(backtest.start_date), 'MMM d, yyyy')} -{' '}
                  {format(new Date(backtest.end_date), 'MMM d, yyyy')}
                </p>
              </div>
              <span
                className={`rounded-full px-3 py-1 text-xs font-medium ${
                  backtest.total_pnl && backtest.total_pnl > 0
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                }`}
              >
                {backtest.total_pnl && backtest.total_pnl > 0 ? '+' : ''}
                {backtest.total_pnl?.toFixed(2) || '0.00'}
              </span>
            </div>

            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-muted-foreground">Sharpe Ratio</p>
                <p className="mt-1 text-lg font-semibold">
                  {backtest.sharpe_ratio?.toFixed(2) || '-'}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Max Drawdown</p>
                <p className="mt-1 text-lg font-semibold">
                  {backtest.max_drawdown ? `${(backtest.max_drawdown * 100).toFixed(1)}%` : '-'}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Win Rate</p>
                <p className="mt-1 text-lg font-semibold">
                  {backtest.win_rate ? `${(backtest.win_rate * 100).toFixed(1)}%` : '-'}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Total Trades</p>
                <p className="mt-1 text-lg font-semibold">{backtest.total_trades || '-'}</p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
