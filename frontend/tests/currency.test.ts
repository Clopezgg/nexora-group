import { describe, expect, it } from 'vitest'
import { formatMoney } from '../src/utils/currency'

describe('formatMoney', () => {
  it('formats HNL with symbol, thousands separator and two decimals', () => {
    const out = formatMoney(150000, 'HNL')
    expect(out).toMatch(/150,000\.00/)
    expect(out).not.toBe('150000')
  })

  it('never renders a bare number for a string input', () => {
    expect(formatMoney('1234.5', 'HNL')).toMatch(/1,234\.50/)
  })

  it('falls back to the default currency when none is given', () => {
    expect(formatMoney(10)).toMatch(/10\.00/)
  })

  it('formats negatives without dropping the sign', () => {
    expect(formatMoney(-2500, 'HNL')).toMatch(/-|\(/)
  })
})
