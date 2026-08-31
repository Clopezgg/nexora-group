import { apiFetch } from './httpClient'

export interface FinancialException {
  code: string
  severity: 'info' | 'warning' | 'critical'
  title: string
  detail: string
  count: number
  suggestedAction: string
  route: string | null
}

export interface ExceptionCenter {
  exceptionZero: boolean
  total: number
  criticalCount: number
  exceptions: FinancialException[]
}

export const exceptionService = {
  list: (companyId: string) =>
    apiFetch<ExceptionCenter>(
      `/financial-control/exceptions?companyId=${encodeURIComponent(companyId)}`,
    ),
}
