import { apiFetch, apiFetchBlob } from './httpClient'
import type {
  BalanceSheetReport,
  BudgetVsActualReport,
  CashFlowReport,
  GeneralLedgerReport,
  IncomeStatementReport,
  SupplierPerformanceRow,
  TrialBalanceReport,
} from '../types/reporting'

export type ReportExportFormat = 'xlsx' | 'pdf'

function exportParams(format: ReportExportFormat, extra?: Record<string, string | undefined>) {
  const params = new URLSearchParams({ format })
  for (const [key, value] of Object.entries(extra ?? {})) {
    if (value) params.set(key, value)
  }
  return params.toString()
}

export const reportingService = {
  getTrialBalance: (companyId: string) =>
    apiFetch<TrialBalanceReport>(`/reports/trial-balance?companyId=${companyId}`),
  exportTrialBalance: (companyId: string, format: ReportExportFormat) =>
    apiFetchBlob(`/reports/trial-balance?companyId=${companyId}&format=${format}`),
  getTrialBalanceXlsx: (companyId: string) =>
    apiFetchBlob(`/reports/trial-balance?companyId=${companyId}&format=xlsx`),
  getBudgetVsActual: (projectId: string) =>
    apiFetch<BudgetVsActualReport>(`/reports/budget-vs-actual?projectId=${projectId}`),
  exportBudgetVsActual: (projectId: string, format: ReportExportFormat) =>
    apiFetchBlob(`/reports/budget-vs-actual/export?projectId=${projectId}&${exportParams(format)}`),
  getBalanceSheet: (companyId: string) =>
    apiFetch<BalanceSheetReport>(`/reports/balance-sheet?companyId=${companyId}`),
  exportBalanceSheet: (companyId: string, format: ReportExportFormat, asOf?: string) =>
    apiFetchBlob(`/reports/balance-sheet/export?companyId=${companyId}&${exportParams(format, { asOf })}`),
  getIncomeStatement: (companyId: string) =>
    apiFetch<IncomeStatementReport>(`/reports/income-statement?companyId=${companyId}`),
  exportIncomeStatement: (
    companyId: string,
    format: ReportExportFormat,
    dateFrom?: string,
    dateTo?: string,
  ) => apiFetchBlob(
    `/reports/income-statement/export?companyId=${companyId}&${exportParams(format, { dateFrom, dateTo })}`,
  ),
  getCashFlow: (companyId: string) =>
    apiFetch<CashFlowReport>(`/reports/cash-flow?companyId=${companyId}`),
  exportCashFlow: (
    companyId: string,
    format: ReportExportFormat,
    dateFrom?: string,
    dateTo?: string,
  ) => apiFetchBlob(
    `/reports/cash-flow/export?companyId=${companyId}&${exportParams(format, { dateFrom, dateTo })}`,
  ),
  getSupplierPerformance: (companyId: string) =>
    apiFetch<SupplierPerformanceRow[]>(`/reports/supplier-performance?companyId=${companyId}`),
  exportSupplierPerformance: (companyId: string, format: ReportExportFormat) =>
    apiFetchBlob(`/reports/supplier-performance/export?companyId=${companyId}&${exportParams(format)}`),
  getGeneralLedger: (companyId: string, offset = 0, limit = 25, accountId?: string) => {
    const params = new URLSearchParams({ companyId, offset: String(offset), limit: String(limit) })
    if (accountId) params.set('accountId', accountId)
    return apiFetch<GeneralLedgerReport>(`/reports/general-ledger?${params.toString()}`)
  },
  exportGeneralLedger: (
    companyId: string,
    format: ReportExportFormat,
    accountId?: string,
    dateFrom?: string,
    dateTo?: string,
  ) => apiFetchBlob(
    `/reports/general-ledger/export?companyId=${companyId}&${exportParams(format, { accountId, dateFrom, dateTo })}`,
  ),
}
