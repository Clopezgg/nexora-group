import { apiFetch } from './httpClient'
import type { DepreciationEntry, FixedAsset } from '../types/asset'

export const assetService = {
  list: (companyId: string) => apiFetch<FixedAsset[]>(`/assets?companyId=${companyId}`),
  create: (payload: {
    companyId: string
    category: string
    name: string
    acquisitionDate: string
    cost: string
    currencyCode: string
    usefulLifeMonths: number
    salvageValue: string
    scope: 'CENTRAL' | 'GENERAL' | 'PROJECT'
    projectId?: string
    depreciationExpenseAccountId: string
    accumulatedDepreciationAccountId: string
  }) => apiFetch<FixedAsset>('/assets', { method: 'POST', body: JSON.stringify(payload) }),
  changeStatus: (assetId: string, status: FixedAsset['status']) =>
    apiFetch<FixedAsset>(`/assets/${assetId}/status`, { method: 'POST', body: JSON.stringify({ status }) }),

  listDepreciationEntries: (assetId: string) =>
    apiFetch<DepreciationEntry[]>(`/assets/${assetId}/depreciation-entries`),
  generateDepreciationEntry: (assetId: string, payload: { periodStart: string; periodEnd: string }) =>
    apiFetch<DepreciationEntry>(`/assets/${assetId}/depreciation-entries`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
