import { apiFetch } from './httpClient'
import type { Rfi } from '../types/rfi'

export const rfiService = {
  list: (companyId: string, projectId?: string) =>
    apiFetch<Rfi[]>(`/rfis?companyId=${companyId}${projectId ? `&projectId=${projectId}` : ''}`),
  get: (rfiId: string) => apiFetch<Rfi>(`/rfis/${rfiId}`),
  create: (payload: {
    companyId: string
    projectId: string
    wbsNodeId?: string | null
    subject: string
    question: string
    responsible?: string
    dueDate?: string
  }) => apiFetch<Rfi>('/rfis', { method: 'POST', body: JSON.stringify(payload) }),
  respond: (rfiId: string, response: string) =>
    apiFetch<Rfi>(`/rfis/${rfiId}/respond`, { method: 'POST', body: JSON.stringify({ response }) }),
  close: (rfiId: string) => apiFetch<Rfi>(`/rfis/${rfiId}/close`, { method: 'POST' }),
}
