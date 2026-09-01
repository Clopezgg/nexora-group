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
  WBSFinancialSummary,
  WBSNode,
  WBSStatus,
} from '../types/project'

export const companyService = {
  list: () => apiFetch<Company[]>('/master-data/companies'),
  create: (name: string, functionalCurrencyCode: string) =>
    apiFetch<Company>('/master-data/companies', { method: 'POST', body: JSON.stringify({ name, functionalCurrencyCode }) }),
}

export interface ProjectInput {
  companyId: string
  name: string
  code?: string
  customerId?: string | null
  manager?: string | null
  managerUserId?: string | null
  currencyCode?: string
  costCenterId?: string | null
  plannedStart?: string | null
  plannedEnd?: string | null
  description?: string | null
  addressLine1?: string | null
  addressLine2?: string | null
  city?: string | null
  stateDepartment?: string | null
  country?: string | null
  locationReference?: string | null
}

export interface BudgetLineInput {
  authorizedAmount: number
  wbsNodeId?: string | null
  economicCategoryId?: string | null
  costCenterId?: string | null
  fiscalPeriodId?: string | null
}

export interface WBSInput {
  code?: string
  name?: string
  parentId?: string | null
  manager?: string | null
  plannedStart?: string | null
  plannedFinish?: string | null
  status?: WBSStatus
  progressPercent?: number
}

export const projectService = {
  list: (companyId: string) => apiFetch<Project[]>(`/projects?company_id=${companyId}`),
  create: (input: ProjectInput) => apiFetch<Project>('/projects', { method: 'POST', body: JSON.stringify(input) }),
  get: (projectId: string) => apiFetch<Project>(`/projects/${projectId}`),
  update: (projectId: string, input: Partial<Omit<ProjectInput, 'companyId'>>) => apiFetch<Project>(`/projects/${projectId}`, { method: 'PATCH', body: JSON.stringify(input) }),
  transitionStatus: (projectId: string, status: ProjectStatus, reason?: string) => apiFetch<Project>(`/projects/${projectId}/status`, { method: 'POST', body: JSON.stringify({ status, reason }) }),
  getFinancialSummary: (projectId: string) => apiFetch<ProjectFinancialSummary>(`/projects/${projectId}/financial-summary`),

  listWbs: (projectId: string) => apiFetch<WBSNode[]>(`/projects/${projectId}/wbs`),
  listWbsFinancials: (projectId: string) => apiFetch<WBSFinancialSummary[]>(`/projects/${projectId}/wbs/financial-summary`),
  createWbs: (projectId: string, input: Required<Pick<WBSInput, 'code' | 'name'>> & WBSInput) => apiFetch<WBSNode>(`/projects/${projectId}/wbs`, { method: 'POST', body: JSON.stringify(input) }),
  updateWbs: (projectId: string, nodeId: string, input: WBSInput) => apiFetch<WBSNode>(`/projects/${projectId}/wbs/${nodeId}`, { method: 'PATCH', body: JSON.stringify(input) }),

  getBudgetSummary: (projectId: string) => apiFetch<BudgetSummary>(`/projects/${projectId}/budgets/summary`),
  getActiveBudget: (projectId: string) => apiFetch<Budget>(`/projects/${projectId}/budgets/active`),
  createBaseline: (projectId: string, input: { currencyCode: string; lines: BudgetLineInput[]; notes?: string }) => apiFetch<Budget>(`/projects/${projectId}/budgets/baseline`, { method: 'POST', body: JSON.stringify(input) }),
  redistributeUnassignedBudget: (projectId: string, input: { lines: BudgetLineInput[]; notes?: string }) => apiFetch<Budget>(`/projects/${projectId}/budgets/redistribute-unassigned`, { method: 'POST', body: JSON.stringify(input) }),
  getForecast: (projectId: string) => apiFetch<Forecast>(`/projects/${projectId}/forecast`),

  listChangeOrders: (projectId: string) => apiFetch<ChangeOrder[]>(`/projects/${projectId}/change-orders`),
  createChangeOrder: (projectId: string, input: { reason: string; wbsNodeId?: string | null; scopeChange?: string; budgetChangeAmount: number; contractChangeAmount: number; scheduleChangeDays?: number | null }) => apiFetch<ChangeOrder>(`/projects/${projectId}/change-orders/detailed`, { method: 'POST', body: JSON.stringify(input) }),
  submitChangeOrder: (changeOrderId: string) => apiFetch<ChangeOrder>(`/projects/change-orders/${changeOrderId}/submit`, { method: 'POST' }),
  approveChangeOrder: (changeOrderId: string) => apiFetch<Budget>(`/projects/change-orders/${changeOrderId}/approve`, { method: 'POST' }),

  listProgress: (projectId: string) => apiFetch<ProgressRecord[]>(`/projects/${projectId}/progress`),
  createProgress: (projectId: string, input: { recordDate: string; plannedPercent: number; actualPercent: number; wbsNodeId?: string | null; description?: string; responsible?: string; evidenceId?: string | null }) => apiFetch<ProgressRecord>(`/projects/${projectId}/progress`, { method: 'POST', body: JSON.stringify(input) }),
}
