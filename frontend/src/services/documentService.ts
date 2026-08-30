import { apiFetch, apiFetchBlob } from './httpClient'
import type { Document, DocumentVersion, Evidence } from '../types/document'

export const documentService = {
  list: (companyId: string, projectId?: string) =>
    apiFetch<Document[]>(
      `/documents?companyId=${companyId}${projectId ? `&projectId=${projectId}` : ''}`,
    ),
  get: (documentId: string) => apiFetch<Document>(`/documents/${documentId}`),
  listVersions: (documentId: string) => apiFetch<DocumentVersion[]>(`/documents/${documentId}/versions`),
  create: (payload: {
    companyId: string
    scope: 'CENTRAL' | 'GENERAL' | 'PROJECT'
    projectId?: string
    category: string
    title: string
    description?: string
    evidenceId: string
  }) => apiFetch<Document>('/documents', { method: 'POST', body: JSON.stringify(payload) }),
  addVersion: (documentId: string, payload: { evidenceId: string; notes?: string }) =>
    apiFetch<DocumentVersion>(`/documents/${documentId}/versions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  listEvidence: (companyId: string, entityType?: string, entityId?: string) => {
    const params = new URLSearchParams({ companyId })
    if (entityType) params.set('entityType', entityType)
    if (entityId) params.set('entityId', entityId)
    return apiFetch<Evidence[]>(`/evidence?${params.toString()}`)
  },
  uploadEvidence: (
    companyId: string,
    file: File,
    category?: string,
    entityType?: string,
    entityId?: string,
  ) => {
    const formData = new FormData()
    formData.append('companyId', companyId)
    if (category) formData.append('category', category)
    if (entityType) formData.append('entityType', entityType)
    if (entityId) formData.append('entityId', entityId)
    formData.append('file', file)
    return apiFetch<Evidence>('/evidence', { method: 'POST', body: formData })
  },
  downloadEvidence: (evidenceId: string) => apiFetchBlob(`/evidence/${evidenceId}/download`),
}
