import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import MarketsPage from './pages/MarketsPage'
import BacktestsPage from './pages/BacktestsPage'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background">
        {/* Navigation */}
        <nav className="border-b">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-8">
                <Link to="/" className="text-2xl font-bold">
                  Kalshi Market Insights
                </Link>
                <div className="flex space-x-4">
                  <Link
                    to="/"
                    className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Markets
                  </Link>
                  <Link
                    to="/backtests"
                    className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Backtests
                  </Link>
                </div>
              </div>
              <div className="text-sm text-muted-foreground">
                Phase 1: Local Analytics
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<MarketsPage />} />
            <Route path="/backtests" element={<BacktestsPage />} />
          </Routes>
        </main>

        {/* Footer */}
        <footer className="border-t mt-16">
          <div className="container mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
            <p>Kalshi Market Insights - Portfolio Demonstration Project</p>
            <p className="mt-1">Not a production trading tool</p>
          </div>
        </footer>
      </div>
    </Router>
  )
}

export default App
