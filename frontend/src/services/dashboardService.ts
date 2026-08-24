import { apiFetch } from './httpClient'
import type { DashboardSummary } from '../types/dashboard'

export const dashboardService = {
  getSummary: () => apiFetch<DashboardSummary>('/dashboard/summary'),
}
