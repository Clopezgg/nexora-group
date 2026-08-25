import { apiFetch } from './httpClient'
import type { BudgetVsActualReport, TrialBalanceReport } from '../types/reporting'

export const reportingService = {
  getTrialBalance: (companyId: string) =>
    apiFetch<TrialBalanceReport>(`/reports/trial-balance?companyId=${companyId}`),
  getBudgetVsActual: (projectId: string) =>
    apiFetch<BudgetVsActualReport>(`/reports/budget-vs-actual?projectId=${projectId}`),
}
