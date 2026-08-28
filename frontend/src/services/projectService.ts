import { apiFetch } from './httpClient'
import type {
  Budget,
  BudgetSummary,
  ChangeOrder,
  Company,
  Forecast,
  Project,
  ProjectFinancialSummary,
  ProjectStatus,
  ProgressRecord,
  WBSNode,
} from '../types/project'

export const companyService = {
  list: () => apiFetch<Company[]>('/master-data/companies'),
  create: (name: string, functionalCurrencyCode: string) =>
    apiFetch<Company>('/master-data/companies', {
      method: 'POST',
      body: JSON.stringify({ name, functionalCurrencyCode }),
    }),
}

export interface ProjectInput {
  companyId: string
  name: string
  code?: string
  customerId?: string
  manager?: string
  currencyCode?: string
  costCenterId?: string
  plannedStart?: string
  plannedEnd?: string
  description?: string
}

export const projectService = {
  list: (companyId: string) => apiFetch<Project[]>(`/projects?company_id=${companyId}`),
  create: (input: ProjectInput) =>
    apiFetch<Project>('/projects', { method: 'POST', body: JSON.stringify(input) }),
  get: (projectId: string) => apiFetch<Project>(`/projects/${projectId}`),
  update: (projectId: string, input: Partial<Omit<ProjectInput, 'companyId'>>) =>
    apiFetch<Project>(`/projects/${projectId}`, { method: 'PATCH', body: JSON.stringify(input) }),
  transitionStatus: (projectId: string, status: ProjectStatus, reason?: string) =>
    apiFetch<Project>(`/projects/${projectId}/status`, {
      method: 'POST',
      body: JSON.stringify({ status, reason }),
    }),
  getFinancialSummary: (projectId: string) =>
    apiFetch<ProjectFinancialSummary>(`/projects/${projectId}/financial-summary`),

  listWbs: (projectId: string) => apiFetch<WBSNode[]>(`/projects/${projectId}/wbs`),
  createWbs: (
    projectId: string,
    input: {
      code: string
      name: string
      parentId?: string | null
      manager?: string
      plannedStart?: string
      plannedFinish?: string
    },
  ) => apiFetch<WBSNode>(`/projects/${projectId}/wbs`, { method: 'POST', body: JSON.stringify(input) }),

  getBudgetSummary: (projectId: string) =>
    apiFetch<BudgetSummary>(`/projects/${projectId}/budgets/summary`),
  getActiveBudget: (projectId: string) => apiFetch<Budget>(`/projects/${projectId}/budgets/active`),
  createBaseline: (
    projectId: string,
    input: {
      currencyCode: string
      lines: Array<{
        authorizedAmount: number
        wbsNodeId?: string | null
        economicCategoryId?: string | null
        costCenterId?: string | null
        fiscalPeriodId?: string | null
      }>
      notes?: string
    },
  ) =>
    apiFetch<Budget>(`/projects/${projectId}/budgets/baseline`, {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  getForecast: (projectId: string) => apiFetch<Forecast>(`/projects/${projectId}/forecast`),

  listChangeOrders: (projectId: string) => apiFetch<ChangeOrder[]>(`/projects/${projectId}/change-orders`),
  createChangeOrder: (
    projectId: string,
    input: {
      reason: string
      wbsNodeId?: string | null
      scopeChange?: string
      budgetChangeAmount: number
      scheduleChangeDays?: number | null
    },
  ) =>
    apiFetch<ChangeOrder>(`/projects/${projectId}/change-orders`, {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  submitChangeOrder: (changeOrderId: string) =>
    apiFetch<ChangeOrder>(`/projects/change-orders/${changeOrderId}/submit`, { method: 'POST' }),
  approveChangeOrder: (changeOrderId: string) =>
    apiFetch<Budget>(`/projects/change-orders/${changeOrderId}/approve`, { method: 'POST' }),

  listProgress: (projectId: string) => apiFetch<ProgressRecord[]>(`/projects/${projectId}/progress`),
  createProgress: (
    projectId: string,
    input: {
      recordDate: string
      plannedPercent: number
      actualPercent: number
      wbsNodeId?: string | null
      description?: string
      responsible?: string
      evidenceId?: string | null
    },
  ) =>
    apiFetch<ProgressRecord>(`/projects/${projectId}/progress`, {
      method: 'POST',
      body: JSON.stringify(input),
    }),
}
