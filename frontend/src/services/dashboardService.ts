import { apiFetch } from './httpClient'
import type { DashboardSummary } from '../types/dashboard'

export const dashboardService = {
  getSummary: (companyId?: string | null) =>
    apiFetch<DashboardSummary>(
      companyId ? `/dashboard/summary?companyId=${companyId}` : '/dashboard/summary',
    ),
}
