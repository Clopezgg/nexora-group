import { apiFetch } from './httpClient'
import type {
  BalanceSheetReport,
  BudgetVsActualReport,
  GeneralLedgerReport,
  IncomeStatementReport,
  TrialBalanceReport,
} from '../types/reporting'

export const reportingService = {
  getTrialBalance: (companyId: string) =>
    apiFetch<TrialBalanceReport>(`/reports/trial-balance?companyId=${companyId}`),
  getBudgetVsActual: (projectId: string) =>
    apiFetch<BudgetVsActualReport>(`/reports/budget-vs-actual?projectId=${projectId}`),
  getBalanceSheet: (companyId: string) =>
    apiFetch<BalanceSheetReport>(`/reports/balance-sheet?companyId=${companyId}`),
  getIncomeStatement: (companyId: string) =>
    apiFetch<IncomeStatementReport>(`/reports/income-statement?companyId=${companyId}`),
  getGeneralLedger: (companyId: string, offset = 0, limit = 25) => {
    const params = new URLSearchParams({
      companyId,
      offset: String(offset),
      limit: String(limit),
    })
    return apiFetch<GeneralLedgerReport>(`/reports/general-ledger?${params.toString()}`)
  },
}
