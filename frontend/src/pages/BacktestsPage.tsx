import { useBacktests } from '../hooks/useBacktests'
import { format } from 'date-fns'

export default function BacktestsPage() {
  const { data, isLoading, error } = useBacktests()
  const backtests = data?.results || []

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
          <p className="mt-4 text-muted-foreground">Loading backtests...</p>
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
            Phase 1 focuses on setting up the infrastructure. Strategy development
            happens in Jupyter notebooks.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Backtests</h1>
        <p className="mt-2 text-muted-foreground">
          Strategy backtesting results and performance metrics
        </p>
      </div>

      <div className="grid gap-4">
        {backtests.map((backtest) => (
          <div key={backtest.id} className="rounded-lg border bg-card p-6">
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
                <p className="mt-1 text-lg font-semibold">
                  {backtest.total_trades || '-'}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
