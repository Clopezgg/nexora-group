import { describe, expect, it } from 'vitest'
import { businessDateDaysAgoIso, businessTodayIso } from '../src/utils/businessDate'

describe('business dates', () => {
  it('uses the Tegucigalpa civil date when UTC is already on the following day', () => {
    const instant = new Date('2026-09-10T02:30:00.000Z')

    expect(businessTodayIso(instant)).toBe('2026-09-09')
    expect(businessDateDaysAgoIso(1, instant)).toBe('2026-09-08')
  })

  it('subtracts calendar days across month boundaries without browser timezone authority', () => {
    const instant = new Date('2026-03-01T12:00:00.000Z')

    expect(businessDateDaysAgoIso(1, instant)).toBe('2026-02-28')
  })
})
