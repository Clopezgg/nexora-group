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
