import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { cashForecastService } from '../../../services/cashForecastService'
import {
  cashFlowActualService,
  type CashFlowGranularity,
  type CashFlowPeriod,
} from '../../../services/cashFlowActualService'
import { formatPeriodLabel } from './periodLabel'

export type CashFlowMode = 'REALIZADO' | 'PROYECTADO'
export type CashFlowRange = '1M' | '3M' | '6M' | '12M'
export type CashFlowGranularityOption = CashFlowGranularity | 'auto'

export const RANGE_DAYS: Record<CashFlowRange, number> = {
  '1M': 30,
  '3M': 90,
  '6M': 182,
  '12M': 365,
}

function isoDaysAgo(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().slice(0, 10)
}
const today = () => new Date().toISOString().slice(0, 10)

const GRANULARITY_LABEL: Record<CashFlowGranularity, string> = {
  day: 'diario',
  week: 'semanal',
  month: 'mensual',
}

export interface CashFlowRow {
  /** Real calendar label — NEVER "S1"/"S2"/"S3" (ORDEN MAESTRA §5/§7). */
  key: string
  inflows: number
  /** Positive magnitude; the chart renders it below the axis. */
  outflows: number
  net: number
  balance: number
  movementCount: number
  periodStart: string | null
  periodEnd: string | null
  /** Present only for REALIZADO rows that can be drilled into. */
  period: CashFlowPeriod | null
}

export interface CashFlowSummaryData {
  openingBalance: number
  totalInflows: number
  totalOutflows: number
  net: number
  closingBalance: number
  dateFrom: string | null
  dateTo: string | null
  granularityLabel: string | null
  currencyCode: string
  liquidityAlert: { minBalance: number; firstNegativeLabel: string | null } | null
}

export interface UseCashFlowSeriesArgs {
  companyId: string | null | undefined
  mode: CashFlowMode
  range: CashFlowRange
  granularity: CashFlowGranularityOption
}

export interface UseCashFlowSeriesResult {
  rows: CashFlowRow[]
  summary: CashFlowSummaryData | null
  hasMovement: boolean
  isLoading: boolean
  isError: boolean
  refetch: () => void
}

/**
 * Única lógica de rango / granularidad / etiquetas / moneda para el flujo de
 * caja (ORDEN MAESTRA §10). La consumen tanto el Home (`HomeForecastCard`) como
 * la página completa (`CashForecastPage`) — no hay dos gráficos incompatibles.
 */
export function useCashFlowSeries({
  companyId,
  mode,
  range,
  granularity,
}: UseCashFlowSeriesArgs): UseCashFlowSeriesResult {
  const from = isoDaysAgo(RANGE_DAYS[range])
  const to = today()

  const seriesQuery = useQuery({
    queryKey: ['cash-flow-series', companyId, from, to, granularity],
    queryFn: () =>
      cashFlowActualService.series({
        companyId: companyId as string,
        from,
        to,
        granularity: granularity === 'auto' ? undefined : granularity,
      }),
    enabled: Boolean(companyId) && mode === 'REALIZADO',
  })

  const forecastQuery = useQuery({
    queryKey: ['cash-forecast', companyId],
    queryFn: () => cashForecastService.get(companyId as string),
    enabled: Boolean(companyId) && mode === 'PROYECTADO',
  })

  const active = mode === 'REALIZADO' ? seriesQuery : forecastQuery

  const rows = useMemo<CashFlowRow[]>(() => {
    if (mode === 'REALIZADO') {
      return (seriesQuery.data?.periods ?? []).map((p) => ({
        key: p.label,
        inflows: p.inflows,
        outflows: Math.abs(p.outflows),
        net: p.net,
        balance: p.closingBalance,
        movementCount: p.movementCount,
        periodStart: p.periodStart,
        periodEnd: p.periodEnd,
        period: p,
      }))
    }
    return (forecastQuery.data?.weeks ?? []).map((w) => ({
      key: formatPeriodLabel(w.weekStart, w.weekEnd),
      inflows: w.inflows,
      outflows: Math.abs(w.outflows),
      net: w.net,
      balance: w.projectedBalance,
      movementCount: 0,
      periodStart: w.weekStart,
      periodEnd: w.weekEnd,
      period: null,
    }))
  }, [mode, seriesQuery.data, forecastQuery.data])

  const summary = useMemo<CashFlowSummaryData | null>(() => {
    if (mode === 'REALIZADO') {
      const s = seriesQuery.data
      if (!s) return null
      return {
        openingBalance: s.openingBalance,
        totalInflows: s.totalInflows,
        totalOutflows: s.totalOutflows,
        net: s.totalInflows - s.totalOutflows,
        closingBalance: s.closingBalance,
        dateFrom: s.dateFrom,
        dateTo: s.dateTo,
        granularityLabel: GRANULARITY_LABEL[s.granularity] ?? null,
        currencyCode: s.currencyCode ?? 'HNL',
        liquidityAlert: null,
      }
    }
    const f = forecastQuery.data
    if (!f) return null
    const totalInflows = f.weeks.reduce((acc, w) => acc + w.inflows, 0)
    const totalOutflows = f.weeks.reduce((acc, w) => acc + Math.abs(w.outflows), 0)
    const firstNegative =
      f.firstNegativeWeekIndex != null ? f.weeks[f.firstNegativeWeekIndex] : null
    return {
      openingBalance: f.openingBalance,
      totalInflows,
      totalOutflows,
      net: totalInflows - totalOutflows,
      closingBalance: f.weeks.at(-1)?.projectedBalance ?? f.openingBalance,
      dateFrom: f.weeks[0]?.weekStart ?? null,
      dateTo: f.weeks.at(-1)?.weekEnd ?? null,
      granularityLabel: 'semanal',
      currencyCode: f.currencyCode ?? 'HNL',
      liquidityAlert: f.hasLiquidityAlert
        ? {
            minBalance: f.minProjectedBalance,
            firstNegativeLabel: firstNegative
              ? formatPeriodLabel(firstNegative.weekStart, firstNegative.weekEnd)
              : null,
          }
        : null,
    }
  }, [mode, seriesQuery.data, forecastQuery.data])

  const hasMovement =
    mode === 'PROYECTADO'
      ? rows.length > 0
      : rows.some((r) => r.inflows !== 0 || r.outflows !== 0)

  return {
    rows,
    summary,
    hasMovement,
    isLoading: active.isLoading,
    isError: active.isError,
    refetch: () => {
      void active.refetch()
    },
  }
}
