import { apiFetch } from './httpClient'

export interface FinancialKpi {
  key: string
  label: string
  value: string
  numeric: number
  severity: 'ok' | 'info' | 'warning' | 'critical'
  hint: string
  route: string | null
}

export interface DailyStatus {
  companyId: string
  asOf: string
  currencyCode: string
  fiscalPeriodLabel: string | null
  fiscalPeriodStatus: string | null
  kpis: FinancialKpi[]
}

export const financialControlService = {
  dailyStatus: (companyId: string) =>
    apiFetch<DailyStatus>(
      `/financial-control/daily-status?companyId=${encodeURIComponent(companyId)}`,
    ),
}

export interface ArMetrics {
  asOf: string
  arOutstanding: string
  trailingCreditSales90d: string
  dso: string | null
  aging: Record<'current' | '1_30' | '31_60' | '61_90' | 'over_90', string>
}

export const arMetricsService = {
  get: (companyId: string) =>
    apiFetch<ArMetrics>(
      `/financial-control/ar-metrics?companyId=${encodeURIComponent(companyId)}`,
    ),
}
