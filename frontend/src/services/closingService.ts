import { apiFetch } from './httpClient'

export interface ClosingCheck {
  key: string
  label: string
  passed: boolean
  blocking: boolean
  detail: string
}

export interface PreCloseChecklist {
  periodId: string
  periodLabel: string
  periodStatus: string
  canHardClose: boolean
  checks: ClosingCheck[]
}

export interface ClosingManifest {
  periodId: string
  periodLabel: string
  companyId: string
  closedAt: string
  forced: boolean
  forceReason: string | null
  checks: ClosingCheck[]
}

export const closingService = {
  checklist: (companyId: string, periodId: string) =>
    apiFetch<PreCloseChecklist>(
      `/accounting/closing/checklist?companyId=${encodeURIComponent(companyId)}&periodId=${encodeURIComponent(periodId)}`,
    ),
  hardClose: (companyId: string, periodId: string, body: { force?: boolean; reason?: string }) =>
    apiFetch<ClosingManifest>(
      `/accounting/closing/${periodId}/hard-close?companyId=${encodeURIComponent(companyId)}`,
      { method: 'POST', body: JSON.stringify(body) },
    ),
}
