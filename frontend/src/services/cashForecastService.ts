import { apiFetch } from './httpClient'

export interface ForecastWeek {
  weekIndex: number
  weekStart: string
  weekEnd: string
  inflows: number
  outflows: number
  net: number
  projectedBalance: number
}

export interface CashForecast {
  asOf: string
  currencyCode: string
  openingBalance: number
  weeks: ForecastWeek[]
  minProjectedBalance: number
  firstNegativeWeekIndex: number | null
  hasLiquidityAlert: boolean
}

export const cashForecastService = {
  get: (companyId: string) =>
    apiFetch<CashForecast>(
      `/financial-control/cash-forecast?companyId=${encodeURIComponent(companyId)}`,
    ),
}
