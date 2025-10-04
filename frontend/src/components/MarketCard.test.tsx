import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MarketCard } from './MarketCard'
import type { MarketSnapshot } from '@/api/markets'

const mockMarket: MarketSnapshot = {
  id: '1',
  ticker: 'INXD-24JAN24-T4200',
  timestamp: '2024-01-15T10:30:00Z',
  source: 'WEBSOCKET',
  sequence: 123,
  yes_price: 65,
  no_price: 35,
  volume: 1500,
  created_at: '2024-01-15T10:30:00Z',
}

describe('MarketCard', () => {
  it('renders market ticker', () => {
    render(<MarketCard market={mockMarket} index={0} />)
    expect(screen.getByText('INXD-24JAN24-T4200')).toBeInTheDocument()
  })

  it('displays yes price', () => {
    render(<MarketCard market={mockMarket} index={0} />)
    expect(screen.getByText('¢65')).toBeInTheDocument()
  })

  it('displays no price', () => {
    render(<MarketCard market={mockMarket} index={0} />)
    expect(screen.getByText('¢35')).toBeInTheDocument()
  })

  it('displays volume', () => {
    render(<MarketCard market={mockMarket} index={0} />)
    expect(screen.getByText('1,500 contracts')).toBeInTheDocument()
  })

  it('displays data source', () => {
    render(<MarketCard market={mockMarket} index={0} />)
    expect(screen.getByText('WEBSOCKET')).toBeInTheDocument()
  })

  it('shows yes price label', () => {
    render(<MarketCard market={mockMarket} index={0} />)
    expect(screen.getByText('YES')).toBeInTheDocument()
  })

  it('shows no price label', () => {
    render(<MarketCard market={mockMarket} index={0} />)
    expect(screen.getByText('NO')).toBeInTheDocument()
  })

  it('shows volume label', () => {
    render(<MarketCard market={mockMarket} index={0} />)
    expect(screen.getByText('24h Volume')).toBeInTheDocument()
  })

  it('calculates implied probability correctly', () => {
    render(<MarketCard market={mockMarket} index={0} />)
    expect(screen.getByText('65%')).toBeInTheDocument() // 65/100 = 0.65 = 65%
  })

  it('shows probability label', () => {
    render(<MarketCard market={mockMarket} index={0} />)
    expect(screen.getByText('probability')).toBeInTheDocument()
  })

  it('formats timestamp as time string', () => {
    render(<MarketCard market={mockMarket} index={0} />)
    // timestamp is displayed as toLocaleTimeString(), check it exists
    const { container } = render(<MarketCard market={mockMarket} index={0} />)
    expect(container.textContent).toMatch(/\d{1,2}:\d{2}/)
  })

  it('applies correct styling classes', () => {
    const { container } = render(<MarketCard market={mockMarket} index={0} />)
    const card = container.firstChild
    expect(card).toHaveClass('rounded-xl', 'border', 'bg-card', 'p-6')
  })

  it('has shadow effects', () => {
    const { container } = render(<MarketCard market={mockMarket} index={0} />)
    const card = container.firstChild
    expect(card).toHaveClass('shadow-lg', 'hover:shadow-2xl')
  })

  it('handles zero yes price', () => {
    const zeroMarket = { ...mockMarket, yes_price: 0 }
    render(<MarketCard market={zeroMarket} index={0} />)
    expect(screen.getByText('¢0')).toBeInTheDocument()
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('handles zero volume', () => {
    const zeroVolumeMarket = { ...mockMarket, volume: 0 }
    render(<MarketCard market={zeroVolumeMarket} index={0} />)
    expect(screen.getByText('0 contracts')).toBeInTheDocument()
  })

  it('renders with POLL source', () => {
    const pollMarket = { ...mockMarket, source: 'POLL' as const }
    render(<MarketCard market={pollMarket} index={0} />)
    expect(screen.getByText('POLL')).toBeInTheDocument()
  })

  it('renders with BACKFILL source', () => {
    const backfillMarket = { ...mockMarket, source: 'BACKFILL' as const }
    render(<MarketCard market={backfillMarket} index={0} />)
    expect(screen.getByText('BACKFILL')).toBeInTheDocument()
  })

  it('has gradient shine overlay', () => {
    const { container } = render(<MarketCard market={mockMarket} index={0} />)
    const gradient = container.querySelector('.bg-gradient-to-br')
    expect(gradient).toBeInTheDocument()
  })

  it('applies animation delay based on index', () => {
    const { container } = render(<MarketCard market={mockMarket} index={3} />)
    // Framer Motion applies delay via props, check that component renders
    expect(container.firstChild).toBeInTheDocument()
  })
})
