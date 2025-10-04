import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Header } from './components/Header'
import { Footer } from './components/Footer'
import MarketsPage from './pages/MarketsPage'
import BacktestsPage from './pages/BacktestsPage'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background flex flex-col">
        <Header />

        {/* Main Content */}
        <main className="container mx-auto px-4 py-8 flex-1">
          <Routes>
            <Route path="/" element={<MarketsPage />} />
            <Route path="/backtests" element={<BacktestsPage />} />
          </Routes>
        </main>

        <Footer />
      </div>
    </Router>
  )
}

export default App
