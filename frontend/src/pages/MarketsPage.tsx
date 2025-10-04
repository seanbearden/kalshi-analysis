import { useMarkets } from '../hooks/useMarkets'

export default function MarketsPage() {
  const { data, isLoading, error } = useMarkets()
  const markets = data?.snapshots || []

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
          <p className="mt-4 text-muted-foreground">Loading markets...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive bg-destructive/10 p-4">
        <h3 className="font-semibold text-destructive">Error Loading Markets</h3>
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

  if (!markets || markets.length === 0) {
    return (
      <div className="rounded-lg border bg-card p-8 text-center">
        <p className="text-muted-foreground">No markets available</p>
        <p className="mt-2 text-sm text-muted-foreground">
          Markets will appear here once the poller fetches data from Kalshi API
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Markets</h1>
        <p className="mt-2 text-muted-foreground">Browse active prediction markets from Kalshi</p>
      </div>

      <div className="rounded-lg border bg-card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-3 text-left text-sm font-semibold">Ticker</th>
                <th className="px-4 py-3 text-right text-sm font-semibold">Yes Price</th>
                <th className="px-4 py-3 text-right text-sm font-semibold">No Price</th>
                <th className="px-4 py-3 text-right text-sm font-semibold">Volume</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Source</th>
                <th className="px-4 py-3 text-left text-sm font-semibold">Last Update</th>
              </tr>
            </thead>
            <tbody>
              {markets.map((market) => (
                <tr key={market.id} className="border-b last:border-0 hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <code className="rounded bg-muted px-2 py-1 text-xs font-mono">
                      {market.ticker}
                    </code>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-sm">
                    {market.yes_price ? `¢${market.yes_price}` : '-'}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-sm">
                    {market.no_price ? `¢${market.no_price}` : '-'}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-sm">
                    {market.volume?.toLocaleString() || '-'}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                        market.source === 'POLL'
                          ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                          : market.source === 'WEBSOCKET'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                            : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                      }`}
                    >
                      {market.source}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">
                    {new Date(market.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mt-4 text-sm text-muted-foreground">
        Showing {markets.length} market{markets.length !== 1 ? 's' : ''}
      </div>
    </div>
  )
}
