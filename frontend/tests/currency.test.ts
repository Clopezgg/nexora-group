import { describe, expect, it } from 'vitest'
import { formatMoney, formatMoneyCompact } from '../src/utils/currency'

describe('formatMoney', () => {
  it('formats HNL with symbol, thousands separator and two decimals', () => {
    const out = formatMoney(150000, 'HNL')
    expect(out).toMatch(/150,000\.00/)
    expect(out).not.toBe('150000')
  })

  it('never renders a bare number for a string input', () => {
    expect(formatMoney('1234.5', 'HNL')).toMatch(/1,234\.50/)
  })

  it('keeps authoritative decimal strings exact at financial boundaries', () => {
    expect(formatMoney('0.30', 'HNL')).toMatch(/0\.30$/)
    // This UI-only number is tolerated for compatibility, but source decimals
    // must not first pass through Number before display.
    expect(formatMoney(0.1 + 0.2, 'HNL')).toMatch(/0\.30$/)
    expect(formatMoney('999999999999.99', 'HNL')).toMatch(/999,999,999,999\.99$/)
    expect(formatMoney('1500000.00', 'HNL')).toMatch(/1,500,000\.00$/)
    expect(formatMoney('1450000.00', 'HNL')).toMatch(/1,450,000\.00$/)
    expect(formatMoney('207142.85', 'HNL')).toMatch(/207,142\.85$/)
  })

  it('rounds decimal and six-place FX display values in cents without floats', () => {
    expect(formatMoney('1.234567', 'HNL')).toMatch(/1\.23$/)
    expect(formatMoney('1.235000', 'HNL')).toMatch(/1\.24$/)
  })

  it('fails closed when currency is blank instead of inventing HNL', () => {
    expect(formatMoney(10, '')).toBe('—')
    expect(formatMoney(10)).toBe('—')
  })

  it('formats negatives without dropping the sign', () => {
    expect(formatMoney(-2500, 'HNL')).toMatch(/-|\(/)
  })
})

describe('formatMoneyCompact', () => {
  it('abbreviates millions and thousands with a currency symbol', () => {
    expect(formatMoneyCompact(1_200_000, 'HNL')).toMatch(/^L\s1\.2M$/)
    expect(formatMoneyCompact(250_000, 'HNL')).toMatch(/^L\s250K$/)
    expect(formatMoneyCompact(980, 'HNL')).toMatch(/^L\s980$/)
  })

  it('keeps the negative sign', () => {
    expect(formatMoneyCompact(-1_500_000, 'HNL')).toMatch(/^-L\s1\.5M$/)
  })

  it('does not invent a currency for compact display', () => {
    expect(formatMoneyCompact(1_000)).toBe('—')
  })
})
