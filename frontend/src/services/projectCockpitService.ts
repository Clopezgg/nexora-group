import { apiFetch } from './httpClient'

export interface ProjectCockpit {
  projectId: string
  projectName: string
  currencyCode: string
  budgetAtCompletion: number
  committed: number
  actualCost: number
  percentComplete: number | null
  earnedValue: number | null
  costPerformanceIndex: number | null
  estimateToComplete: number | null
  estimateAtCompletion: number | null
  varianceAtCompletion: number | null
  contractRevenue: number
  projectedMargin: number | null
  projectedMarginPct: number | null
}

export const projectCockpitService = {
  get: (projectId: string) =>
    apiFetch<ProjectCockpit>(`/projects/${projectId}/financial-cockpit`),
}
