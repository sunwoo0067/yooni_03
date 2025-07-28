import { describe, it, expect } from 'vitest'
import { formatCurrency, formatDate, formatPercentage } from './format'

describe('formatCurrency', () => {
  it('formats number as Korean currency', () => {
    expect(formatCurrency(1000)).toBe('₩1,000')
    expect(formatCurrency(1234567)).toBe('₩1,234,567')
    expect(formatCurrency(0)).toBe('₩0')
  })
})

describe('formatDate', () => {
  it('formats date in Korean format', () => {
    const date = new Date('2024-07-25')
    expect(formatDate(date)).toContain('2024년')
    expect(formatDate(date)).toContain('7월')
    expect(formatDate(date)).toContain('25일')
  })

  it('accepts string date', () => {
    expect(formatDate('2024-07-25')).toContain('2024년')
  })
})

describe('formatPercentage', () => {
  it('formats decimal as percentage', () => {
    expect(formatPercentage(0.1)).toBe('10.0%')
    expect(formatPercentage(0.567)).toBe('56.7%')
    expect(formatPercentage(1)).toBe('100.0%')
    expect(formatPercentage(0)).toBe('0.0%')
  })
})