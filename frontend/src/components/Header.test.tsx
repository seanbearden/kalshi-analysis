import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { Header } from './Header'

const renderHeader = (initialRoute = '/') => {
  window.history.pushState({}, 'Test page', initialRoute)
  return render(
    <BrowserRouter>
      <Header />
    </BrowserRouter>
  )
}

describe('Header', () => {
  it('renders the logo with correct text', () => {
    renderHeader()
    expect(screen.getByText('Kalshi Insights')).toBeInTheDocument()
  })

  it('renders navigation links', () => {
    renderHeader()
    expect(screen.getByText('Markets')).toBeInTheDocument()
    expect(screen.getByText('Backtests')).toBeInTheDocument()
  })

  it('highlights active route on Markets page', () => {
    renderHeader('/')
    const marketsDiv = screen.getByText('Markets').closest('div')
    expect(marketsDiv).toHaveClass('text-foreground')
  })

  it('highlights active route on Backtests page', () => {
    renderHeader('/backtests')
    const backtestsDiv = screen.getByText('Backtests').closest('div')
    expect(backtestsDiv).toHaveClass('text-foreground')
  })

  it('renders TrendingUp icon in logo', () => {
    const { container } = renderHeader()
    const logo = container.querySelector('.h-10.w-10')
    expect(logo).toBeInTheDocument()
  })

  it('renders navigation icons', () => {
    const { container } = renderHeader()
    const icons = container.querySelectorAll('.h-4.w-4')
    expect(icons.length).toBeGreaterThanOrEqual(2) // At least 2 nav icons
  })

  it('has sticky positioning', () => {
    const { container } = renderHeader()
    const header = container.querySelector('header')
    expect(header).toHaveClass('sticky', 'top-0', 'z-50')
  })

  it('has backdrop blur effect', () => {
    const { container } = renderHeader()
    const header = container.querySelector('header')
    expect(header).toHaveClass('backdrop-blur')
  })

  it('logo links to home page', () => {
    renderHeader()
    const logo = screen.getByText('Kalshi Insights').closest('a')
    expect(logo).toHaveAttribute('href', '/')
  })

  it('Markets link navigates to root', () => {
    renderHeader()
    const marketsLink = screen.getByText('Markets').closest('a')
    expect(marketsLink).toHaveAttribute('href', '/')
  })

  it('Backtests link navigates to /backtests', () => {
    renderHeader()
    const backtestsLink = screen.getByText('Backtests').closest('a')
    expect(backtestsLink).toHaveAttribute('href', '/backtests')
  })

  it('renders with flexbox layout', () => {
    const { container } = renderHeader()
    const flexContainer = container.querySelector('.flex.items-center.justify-between')
    expect(flexContainer).toBeInTheDocument()
  })

  it('applies gradient to logo background', () => {
    const { container } = renderHeader()
    const logoBackground = container.querySelector('.bg-gradient-to-br')
    expect(logoBackground).toBeInTheDocument()
  })
})
