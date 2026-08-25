import { apiFetch } from './httpClient'
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

  // Sube el archivo real (multipart/form-data) a Azure Blob vía el backend
  // y devuelve la metadata de Evidence -- el `id` resultante es lo que
  // documentService.create/addVersion esperan como `evidenceId`. Si el
  // backend no tiene EVIDENCE_BACKEND configurado, esta llamada rechaza con
  // un 503 real (NXR-EVIDENCE-001), nunca con una URL fabricada.
  uploadEvidence: (companyId: string, file: File, category?: string) => {
    const formData = new FormData()
    formData.append('companyId', companyId)
    if (category) formData.append('category', category)
    formData.append('file', file)
    return apiFetch<Evidence>('/evidence', { method: 'POST', body: formData })
  },
}
