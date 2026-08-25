import { apiFetch } from './httpClient'
import type { DailySiteReport, DailySiteReportPhoto } from '../types/siteReport'

export const siteReportService = {
  list: (projectId: string) => apiFetch<DailySiteReport[]>(`/site-reports?projectId=${projectId}`),
  get: (reportId: string) => apiFetch<DailySiteReport>(`/site-reports/${reportId}`),
  create: (payload: {
    projectId: string
    reportDate: string
    weather?: string
    workforceSummary?: string
    activitiesPerformed: string
    equipmentUsed?: string
    materialsUsed?: string
    incidents?: string
    observations?: string
  }) => apiFetch<DailySiteReport>('/site-reports', { method: 'POST', body: JSON.stringify(payload) }),
  attachPhoto: (reportId: string, evidenceId: string) =>
    apiFetch<DailySiteReportPhoto>(`/site-reports/${reportId}/photos`, {
      method: 'POST',
      body: JSON.stringify({ evidenceId }),
    }),
  submit: (reportId: string) =>
    apiFetch<DailySiteReport>(`/site-reports/${reportId}/submit`, { method: 'POST' }),
  approve: (reportId: string) =>
    apiFetch<DailySiteReport>(`/site-reports/${reportId}/approve`, { method: 'POST' }),
  reject: (reportId: string) =>
    apiFetch<DailySiteReport>(`/site-reports/${reportId}/reject`, { method: 'POST' }),
}
