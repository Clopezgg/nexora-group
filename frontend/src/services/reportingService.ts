import { apiFetch } from './httpClient'
import type {
  BalanceSheetReport,
  BudgetVsActualReport,
  CashFlowReport,
  GeneralLedgerReport,
  IncomeStatementReport,
  SupplierPerformanceRow,
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
  getCashFlow: (companyId: string) =>
    apiFetch<CashFlowReport>(`/reports/cash-flow?companyId=${companyId}`),
  getSupplierPerformance: (companyId: string) =>
    apiFetch<SupplierPerformanceRow[]>(`/reports/supplier-performance?companyId=${companyId}`),
  getGeneralLedger: (companyId: string, offset = 0, limit = 25) => {
    const params = new URLSearchParams({
      companyId,
      offset: String(offset),
      limit: String(limit),
    })
    return apiFetch<GeneralLedgerReport>(`/reports/general-ledger?${params.toString()}`)
  },
}
