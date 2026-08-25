import { apiFetch } from './httpClient'
import type { SafetyIncident, SafetyObservation, SafetySeverity } from '../types/safety'

export const safetyService = {
  listObservations: (projectId: string) =>
    apiFetch<SafetyObservation[]>(`/safety/observations?projectId=${projectId}`),
  createObservation: (payload: {
    projectId: string
    observationDate: string
    category: string
    description: string
    severity: SafetySeverity
    responsibleUserId?: string
    correctiveAction?: string
    evidenceId?: string
  }) =>
    apiFetch<SafetyObservation>('/safety/observations', { method: 'POST', body: JSON.stringify(payload) }),
  closeObservation: (observationId: string) =>
    apiFetch<SafetyObservation>(`/safety/observations/${observationId}/close`, { method: 'POST' }),

  listIncidents: (projectId: string) =>
    apiFetch<SafetyIncident[]>(`/safety/incidents?projectId=${projectId}`),
  createIncident: (payload: {
    projectId: string
    incidentDate: string
    description: string
    severity: SafetySeverity
    responsibleUserId?: string
    correctiveAction?: string
    evidenceId?: string
  }) => apiFetch<SafetyIncident>('/safety/incidents', { method: 'POST', body: JSON.stringify(payload) }),
  closeIncident: (incidentId: string) =>
    apiFetch<SafetyIncident>(`/safety/incidents/${incidentId}/close`, { method: 'POST' }),
}
