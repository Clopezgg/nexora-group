import { apiFetch } from './httpClient'
import type { AuditLogEntry } from '../types/audit'

export const auditService = {
  list: (params: { companyId: string; entityType?: string; entityId?: string }) => {
    const query = new URLSearchParams({ companyId: params.companyId })
    if (params.entityType) query.set('entityType', params.entityType)
    if (params.entityId) query.set('entityId', params.entityId)
    return apiFetch<AuditLogEntry[]>(`/audit?${query.toString()}`)
  },
}
