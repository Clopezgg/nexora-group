import { describe, expect, it } from 'vitest'
import { formatPeriodLabel } from '../src/features/finance/cashflow/periodLabel'

describe('formatPeriodLabel', () => {
  it('renders a single day as "13 sep"', () => {
    expect(formatPeriodLabel('2026-09-13', '2026-09-13')).toBe('13 sep')
  })

  it('renders a full calendar month as "Septiembre 2026"', () => {
    expect(formatPeriodLabel('2026-09-01', '2026-09-30')).toBe('Septiembre 2026')
    expect(formatPeriodLabel('2026-02-01', '2026-02-28')).toBe('Febrero 2026')
  })

  it('renders a week inside one month as "1–7 sep"', () => {
    expect(formatPeriodLabel('2026-09-01', '2026-09-07')).toBe('1–7 sep')
  })

  it('renders a week spanning two months as "28 ago – 3 sep"', () => {
    expect(formatPeriodLabel('2026-08-28', '2026-09-03')).toBe('28 ago – 3 sep')
  })

  it('never emits an "S1"-style label', () => {
    const label = formatPeriodLabel('2026-07-06', '2026-07-12')
    expect(label).not.toMatch(/^S\d+$/)
  })
})
