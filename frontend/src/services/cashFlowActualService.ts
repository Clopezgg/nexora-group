import { apiFetch } from './httpClient'

export interface ActualWeek {
  weekIndex: number
  weekStart: string
  weekEnd: string
  inflows: number
  outflows: number
  net: number
  closingBalance: number
  byCategory: Record<string, number>
}

export interface CashFlowActual {
  asOf: string
  currencyCode: string
  openingBalance: number
  closingBalance: number
  totalInflows: number
  totalOutflows: number
  inflowByCategory: Record<string, number>
  outflowByCategory: Record<string, number>
  weeks: ActualWeek[]
}

/**
 * Flujo de caja REALIZADO — últimas 13 semanas. Distinto del forecast
 * (`cashForecastService`, que proyecta AP/AR futuros): esto ya ocurrió,
 * leído del movimiento real de las cuentas de tesorería.
 */
export const cashFlowActualService = {
  get: (companyId: string) =>
    apiFetch<CashFlowActual>(
      `/financial-control/cash-flow-actual?companyId=${encodeURIComponent(companyId)}`,
    ),
}
