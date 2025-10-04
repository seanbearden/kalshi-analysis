import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Footer } from './Footer'

describe('Footer', () => {
  it('renders copyright text with current year', () => {
    render(<Footer />)
    const currentYear = new Date().getFullYear()
    expect(screen.getByText(new RegExp(`${currentYear}`))).toBeInTheDocument()
  })

  it('renders project title', () => {
    render(<Footer />)
    expect(screen.getByText(/Kalshi Market Insights/i)).toBeInTheDocument()
  })

  it('renders GitHub social link', () => {
    render(<Footer />)
    const githubLink = screen.getByLabelText('GitHub')
    expect(githubLink).toHaveAttribute('href', 'https://github.com/seanbearden')
  })

  it('renders Twitter social link', () => {
    render(<Footer />)
    const twitterLink = screen.getByLabelText('Twitter')
    expect(twitterLink).toHaveAttribute('href', 'https://twitter.com')
  })

  it('renders LinkedIn social link', () => {
    render(<Footer />)
    const linkedinLink = screen.getByLabelText('LinkedIn')
    expect(linkedinLink).toHaveAttribute('href', 'https://linkedin.com')
  })

  it('opens social links in new tab', () => {
    render(<Footer />)
    const githubLink = screen.getByLabelText('GitHub')
    expect(githubLink).toHaveAttribute('target', '_blank')
    expect(githubLink).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('has border at top', () => {
    const { container } = render(<Footer />)
    const footer = container.querySelector('footer')
    expect(footer).toHaveClass('border-t')
  })

  it('applies muted background', () => {
    const { container } = render(<Footer />)
    const footer = container.querySelector('footer')
    expect(footer).toHaveClass('bg-muted/30')
  })

  it('renders social icons', () => {
    const { container } = render(<Footer />)
    const icons = container.querySelectorAll('svg')
    expect(icons.length).toBe(3) // GitHub, Twitter, LinkedIn
  })

  it('has responsive layout classes', () => {
    const { container } = render(<Footer />)
    const layout = container.querySelector('.flex-col')
    expect(layout).toHaveClass('md:flex-row')
  })

  it('applies hover styles to social links', () => {
    render(<Footer />)
    const socialLink = screen.getByLabelText('GitHub')
    expect(socialLink).toHaveClass('hover:text-foreground')
  })

  it('centers content in container', () => {
    const { container } = render(<Footer />)
    const contentWrapper = container.querySelector('.items-center')
    expect(contentWrapper).toBeInTheDocument()
  })
})
