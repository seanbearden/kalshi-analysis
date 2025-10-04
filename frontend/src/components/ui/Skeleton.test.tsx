import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { Skeleton, MarketCardSkeleton, BacktestCardSkeleton } from './Skeleton'

describe('Skeleton', () => {
  it('renders with default rectangular variant', () => {
    const { container } = render(<Skeleton />)
    const skeleton = container.firstChild
    expect(skeleton).toHaveClass('rounded-md')
  })

  it('renders with text variant', () => {
    const { container } = render(<Skeleton variant="text" />)
    const skeleton = container.firstChild
    expect(skeleton).toHaveClass('h-4', 'rounded')
  })

  it('renders with circular variant', () => {
    const { container } = render(<Skeleton variant="circular" />)
    const skeleton = container.firstChild
    expect(skeleton).toHaveClass('rounded-full')
  })

  it('applies custom className', () => {
    const { container } = render(<Skeleton className="w-full h-20" />)
    const skeleton = container.firstChild
    expect(skeleton).toHaveClass('w-full', 'h-20')
  })

  it('has pulse animation', () => {
    const { container } = render(<Skeleton />)
    const skeleton = container.firstChild
    expect(skeleton).toHaveClass('animate-pulse')
  })

  it('has muted background', () => {
    const { container } = render(<Skeleton />)
    const skeleton = container.firstChild
    expect(skeleton).toHaveClass('bg-muted')
  })
})

describe('MarketCardSkeleton', () => {
  it('renders card container', () => {
    const { container } = render(<MarketCardSkeleton />)
    const card = container.querySelector('.rounded-xl.border.bg-card.p-6')
    expect(card).toBeInTheDocument()
  })

  it('renders ticker skeleton', () => {
    const { container } = render(<MarketCardSkeleton />)
    const ticker = container.querySelector('.h-5.w-24')
    expect(ticker).toBeInTheDocument()
  })

  it('renders subtitle skeleton', () => {
    const { container } = render(<MarketCardSkeleton />)
    const subtitle = container.querySelector('.h-4.w-32')
    expect(subtitle).toBeInTheDocument()
  })

  it('renders status badge skeleton', () => {
    const { container } = render(<MarketCardSkeleton />)
    const badge = container.querySelector('.h-8.w-20')
    expect(badge).toBeInTheDocument()
  })

  it('renders grid layout for metrics', () => {
    const { container } = render(<MarketCardSkeleton />)
    const grid = container.querySelector('.grid.grid-cols-2.gap-4')
    expect(grid).toBeInTheDocument()
  })

  it('renders metric label skeletons', () => {
    const { container } = render(<MarketCardSkeleton />)
    const labels = container.querySelectorAll('.h-3.w-16')
    expect(labels.length).toBeGreaterThan(0)
  })

  it('renders metric value skeletons', () => {
    const { container } = render(<MarketCardSkeleton />)
    const values = container.querySelectorAll('.h-6.w-24')
    expect(values.length).toBeGreaterThan(0)
  })

  it('has shadow styling', () => {
    const { container } = render(<MarketCardSkeleton />)
    const card = container.querySelector('.shadow-lg')
    expect(card).toBeInTheDocument()
  })
})

describe('BacktestCardSkeleton', () => {
  it('renders card container', () => {
    const { container } = render(<BacktestCardSkeleton />)
    const card = container.querySelector('.rounded-xl.border.bg-card.p-6')
    expect(card).toBeInTheDocument()
  })

  it('renders strategy name skeleton', () => {
    const { container } = render(<BacktestCardSkeleton />)
    const name = container.querySelector('.h-6.w-40')
    expect(name).toBeInTheDocument()
  })

  it('renders description skeleton', () => {
    const { container } = render(<BacktestCardSkeleton />)
    const description = container.querySelector('.h-4.w-48')
    expect(description).toBeInTheDocument()
  })

  it('renders status badge skeleton', () => {
    const { container } = render(<BacktestCardSkeleton />)
    const badge = container.querySelector('.h-7.w-20.rounded-full')
    expect(badge).toBeInTheDocument()
  })

  it('renders grid layout for metrics', () => {
    const { container } = render(<BacktestCardSkeleton />)
    const grid = container.querySelector('.grid.grid-cols-2.md\\:grid-cols-4.gap-4')
    expect(grid).toBeInTheDocument()
  })

  it('renders metric groups', () => {
    const { container } = render(<BacktestCardSkeleton />)
    const metricGroups = container.querySelectorAll('.space-y-2')
    expect(metricGroups.length).toBeGreaterThan(0)
  })

  it('renders metric label skeletons', () => {
    const { container } = render(<BacktestCardSkeleton />)
    const labels = container.querySelectorAll('.h-3.w-20')
    expect(labels.length).toBe(4)
  })

  it('renders metric value skeletons', () => {
    const { container } = render(<BacktestCardSkeleton />)
    const values = container.querySelectorAll('.h-6.w-16')
    expect(values.length).toBe(4)
  })

  it('has shadow styling', () => {
    const { container } = render(<BacktestCardSkeleton />)
    const card = container.querySelector('.shadow-lg')
    expect(card).toBeInTheDocument()
  })

  it('has margin bottom spacing', () => {
    const { container } = render(<BacktestCardSkeleton />)
    const header = container.querySelector('.mb-4')
    expect(header).toBeInTheDocument()
  })
})
