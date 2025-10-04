import { describe, it, expect } from 'vitest'
import { formatCurrency, formatPercentage, formatNumber } from './format'

describe('formatCurrency', () => {
  it('formats positive values', () => {
    expect(formatCurrency(100)).toBe('$100.00')
    expect(formatCurrency(1234.56)).toBe('$1,234.56')
  })

  it('formats negative values', () => {
    expect(formatCurrency(-100)).toBe('-$100.00')
  })

  it('formats zero', () => {
    expect(formatCurrency(0)).toBe('$0.00')
  })
})

describe('formatPercentage', () => {
  it('formats decimal values as percentages', () => {
    expect(formatPercentage(0.5)).toBe('50.0%')
    expect(formatPercentage(0.123)).toBe('12.3%')
  })

  it('respects decimal places parameter', () => {
    expect(formatPercentage(0.12345, 2)).toBe('12.35%')
    expect(formatPercentage(0.12345, 0)).toBe('12%')
  })

  it('handles edge cases', () => {
    expect(formatPercentage(0)).toBe('0.0%')
    expect(formatPercentage(1)).toBe('100.0%')
  })
})

describe('formatNumber', () => {
  it('formats numbers less than 1000 without suffix', () => {
    expect(formatNumber(999)).toBe('999')
    expect(formatNumber(0)).toBe('0')
  })

  it('formats thousands with k suffix', () => {
    expect(formatNumber(1000)).toBe('1.0k')
    expect(formatNumber(5500)).toBe('5.5k')
  })

  it('formats millions with M suffix', () => {
    expect(formatNumber(1_000_000)).toBe('1.0M')
    expect(formatNumber(2_500_000)).toBe('2.5M')
  })

  it('formats billions with B suffix', () => {
    expect(formatNumber(1_000_000_000)).toBe('1.0B')
    expect(formatNumber(3_200_000_000)).toBe('3.2B')
  })
})
