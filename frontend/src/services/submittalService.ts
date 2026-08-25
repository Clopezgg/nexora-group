import { apiFetch } from './httpClient'
import type { Submittal } from '../types/submittal'

export const submittalService = {
  list: (companyId: string, projectId?: string) =>
    apiFetch<Submittal[]>(
      `/submittals?companyId=${companyId}${projectId ? `&projectId=${projectId}` : ''}`,
    ),
  get: (submittalId: string) => apiFetch<Submittal>(`/submittals/${submittalId}`),
  create: (payload: {
    companyId: string
    projectId: string
    wbsNodeId?: string | null
    title: string
    description?: string
    supplierId?: string | null
    contractId?: string | null
    submittedAt: string
    dueDate?: string
    evidenceId?: string | null
  }) => apiFetch<Submittal>('/submittals', { method: 'POST', body: JSON.stringify(payload) }),
  recordResponse: (submittalId: string, response: string) =>
    apiFetch<Submittal>(`/submittals/${submittalId}/response`, {
      method: 'POST',
      body: JSON.stringify({ response }),
    }),
  decide: (submittalId: string, decision: 'APPROVED' | 'REJECTED') =>
    apiFetch<Submittal>(`/submittals/${submittalId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision }),
    }),
}
