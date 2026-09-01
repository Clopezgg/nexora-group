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
export type CashFlowGranularity = 'day' | 'week' | 'month'

export interface CashFlowPeriod {
  index: number
  periodStart: string
  periodEnd: string
  label: string
  inflows: number
  outflows: number
  net: number
  closingBalance: number
  movementCount: number
  byCategory: Record<string, number>
}

export interface CashFlowSeries {
  dateFrom: string
  dateTo: string
  granularity: CashFlowGranularity
  currencyCode: string
  openingBalance: number
  closingBalance: number
  totalInflows: number
  totalOutflows: number
  inflowByCategory: Record<string, number>
  outflowByCategory: Record<string, number>
  periods: CashFlowPeriod[]
}

export interface CashFlowMovement {
  documentId: string
  documentNumber: string
  effectiveDate: string
  direction: 'INFLOW' | 'OUTFLOW'
  category: string
  amount: number
  concept: string | null
  counterparty: string | null
}

export const cashFlowActualService = {
  /**
   * @deprecated Forma "weeks" legacy (`S1..S13`). Sin consumidores en la UI
   * desde la ORDEN MAESTRA §5/§10 — Home y CashForecastPage usan `series()` con
   * rangos y etiquetas de calendario reales. Conservado solo por compatibilidad
   * del endpoint; no usar en pantallas nuevas.
   */
  get: (companyId: string) =>
    apiFetch<CashFlowActual>(
      `/financial-control/cash-flow-actual?companyId=${encodeURIComponent(companyId)}`,
    ),

  /**
   * Serie sobre un rango de fechas REAL con granularidad Auto/Día/Semana/Mes
   * y etiquetas de calendario (§10/§11). `granularity` omitido = Auto.
   */
  series: (params: {
    companyId: string
    from: string
    to: string
    granularity?: CashFlowGranularity
  }) => {
    const q = new URLSearchParams({ companyId: params.companyId, from: params.from, to: params.to })
    if (params.granularity) q.set('granularity', params.granularity)
    return apiFetch<CashFlowSeries>(`/financial-control/cash-flow-actual/series?${q.toString()}`)
  },

  /** Drill-down: los movimientos individuales de un rango. */
  movements: (params: { companyId: string; from: string; to: string }) => {
    const q = new URLSearchParams(params as Record<string, string>)
    return apiFetch<CashFlowMovement[]>(
      `/financial-control/cash-flow-actual/movements?${q.toString()}`,
    )
  },
}
