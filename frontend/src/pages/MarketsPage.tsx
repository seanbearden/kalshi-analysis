import { useMarkets } from '../hooks/useMarkets'
import { MarketCard } from '../components/MarketCard'
import { MarketCardSkeleton } from '../components/ui/Skeleton'
import { motion } from 'framer-motion'

export default function MarketsPage() {
  const { data, isLoading, error } = useMarkets()
  const markets = data?.snapshots || []

  if (isLoading) {
    return (
      <div>
        <div className="mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
            Markets
          </h1>
          <p className="mt-3 text-lg text-muted-foreground">
            Browse active prediction markets from Kalshi
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <MarketCardSkeleton key={i} />
          ))}
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
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5 }}>
      <div className="mb-8">
        <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-600 to-cyan-600 bg-clip-text text-transparent">
          Markets
        </h1>
        <p className="mt-3 text-lg text-muted-foreground">
          Browse active prediction markets from Kalshi
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {markets.map((market, index) => (
          <MarketCard key={market.id} market={market} index={index} />
        ))}
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="mt-6 text-sm text-muted-foreground"
      >
        Showing {markets.length} market{markets.length !== 1 ? 's' : ''}
      </motion.div>
    </motion.div>
  )
}
