import { apiFetch } from './httpClient'
import type { CorrectiveAction, NonConformance, QualityInspection } from '../types/quality'

export const qualityService = {
  listInspections: (projectId: string) =>
    apiFetch<QualityInspection[]>(`/quality/inspections?projectId=${projectId}`),
  createInspection: (payload: {
    projectId: string
    inspectionType: string
    inspectionDate: string
    result?: 'PENDING' | 'PASS' | 'FAIL'
    notes?: string
    evidenceId?: string
  }) => apiFetch<QualityInspection>('/quality/inspections', { method: 'POST', body: JSON.stringify(payload) }),

  listNonConformances: (projectId: string) =>
    apiFetch<NonConformance[]>(`/quality/non-conformances?projectId=${projectId}`),
  createNonConformance: (payload: {
    projectId: string
    qualityInspectionId?: string
    description: string
    responsibleUserId: string
    dueDate?: string
    evidenceId?: string
  }) =>
    apiFetch<NonConformance>('/quality/non-conformances', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  closeNonConformance: (nonConformanceId: string) =>
    apiFetch<NonConformance>(`/quality/non-conformances/${nonConformanceId}/close`, {
      method: 'POST',
    }),

  listCorrectiveActions: (nonConformanceId: string) =>
    apiFetch<CorrectiveAction[]>(`/quality/non-conformances/${nonConformanceId}/corrective-actions`),
  createCorrectiveAction: (
    nonConformanceId: string,
    payload: { description: string; responsibleUserId: string; dueDate: string; evidenceId?: string },
  ) =>
    apiFetch<CorrectiveAction>(`/quality/non-conformances/${nonConformanceId}/corrective-actions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  completeCorrectiveAction: (correctiveActionId: string) =>
    apiFetch<CorrectiveAction>(`/quality/corrective-actions/${correctiveActionId}/complete`, {
      method: 'POST',
    }),
}
