import { apiFetch } from './httpClient'
import type { ApprovalRequestEntry } from '../types/approval'

export const approvalService = {
  list: (params: { companyId: string; module?: string }) => {
    const query = new URLSearchParams({ companyId: params.companyId })
    if (params.module) query.set('module', params.module)
    return apiFetch<ApprovalRequestEntry[]>(`/approvals?${query.toString()}`)
  },
  decide: (requestId: string, decision: 'APPROVED' | 'REJECTED', comment?: string) =>
    apiFetch<ApprovalRequestEntry>(`/approvals/${requestId}/decide`, {
      method: 'POST',
      body: JSON.stringify({ decision, comment: comment || undefined }),
    }),
}
