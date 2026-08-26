import { apiFetch } from './httpClient'
import type {
  Budget,
  BudgetSummary,
  ChangeOrder,
  Company,
  Forecast,
  Project,
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

export const projectService = {
  list: (companyId: string) => apiFetch<Project[]>(`/projects?company_id=${companyId}`),
  create: (input: { companyId: string; name: string; code?: string; currencyCode?: string }) =>
    apiFetch<Project>('/projects', { method: 'POST', body: JSON.stringify(input) }),
  get: (projectId: string) => apiFetch<Project>(`/projects/${projectId}`),

  listWbs: (projectId: string) => apiFetch<WBSNode[]>(`/projects/${projectId}/wbs`),
  createWbs: (
    projectId: string,
    input: { code: string; name: string; parentId?: string | null },
  ) => apiFetch<WBSNode>(`/projects/${projectId}/wbs`, { method: 'POST', body: JSON.stringify(input) }),

  getBudgetSummary: (projectId: string) =>
    apiFetch<BudgetSummary>(`/projects/${projectId}/budgets/summary`),
  getActiveBudget: (projectId: string) => apiFetch<Budget>(`/projects/${projectId}/budgets/active`),
  createBaseline: (
    projectId: string,
    input: { currencyCode: string; lines: { authorizedAmount: number; wbsNodeId?: string | null }[] },
  ) =>
    apiFetch<Budget>(`/projects/${projectId}/budgets/baseline`, {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  getForecast: (projectId: string) => apiFetch<Forecast>(`/projects/${projectId}/forecast`),

  listChangeOrders: (projectId: string) => apiFetch<ChangeOrder[]>(`/projects/${projectId}/change-orders`),
  createChangeOrder: (
    projectId: string,
    input: { reason: string; budgetChangeAmount: number },
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
    input: { recordDate: string; plannedPercent: number; actualPercent: number; description?: string },
  ) =>
    apiFetch<ProgressRecord>(`/projects/${projectId}/progress`, {
      method: 'POST',
      body: JSON.stringify(input),
    }),
}
