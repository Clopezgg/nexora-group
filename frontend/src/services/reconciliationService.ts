import { apiFetch } from './httpClient'

export interface ReconciliationLine {
  subledger: 'TREASURY' | 'ACCOUNTS_PAYABLE' | 'ACCOUNTS_RECEIVABLE'
  subledgerTotal: number
  glTotal: number
  difference: number
  reconciled: boolean
  detail: string
}

export interface SubledgerGlReconciliation {
  allReconciled: boolean
  lines: ReconciliationLine[]
}

export const reconciliationService = {
  subledgerGl: (companyId: string) =>
    apiFetch<SubledgerGlReconciliation>(
      `/accounting/reconciliation/subledger-gl?companyId=${encodeURIComponent(companyId)}`,
    ),
}
