export interface Company {
  id: string
  name: string
  code: string | null
  legalName: string | null
  functionalCurrencyCode: string | null
  country: string | null
  fiscalId: string | null
}

export type ProjectStatus =
  | 'PLANNING'
  | 'ACTIVE'
  | 'ON_HOLD'
  | 'COMPLETED'
  | 'CLOSED'
  | 'CANCELLED'

export type WBSStatus = 'PLANNING' | 'ACTIVE' | 'ON_HOLD' | 'COMPLETED' | 'CANCELLED'

export interface Project {
  id: string
  companyId: string
  name: string
  code: string | null
  customerId: string | null
  customerRef: string | null
  manager: string | null
  managerUserId: string | null
  currencyCode: string | null
  costCenterId: string | null
  plannedStart: string | null
  plannedEnd: string | null
  actualEnd: string | null
  status: ProjectStatus
  description: string | null
  addressLine1: string | null
  addressLine2: string | null
  city: string | null
  stateDepartment: string | null
  country: string | null
  locationReference: string | null
}

export interface ProjectFinancialSummary {
  projectId: string
  currencyCode: string
  contractValue: string | null
  baselineBudget: string | null
  currentBudget: string | null
  committed: string
  poCommitted: string
  executionContractValue: string
  executionContractPaid: string
  executionContractBalance: string
  accrued: string
  paid: string
  available: string | null
  invoiced: string
  collected: string
  receivablesOutstanding: string
  recognizedRevenue: string
  actualCost: string
  expectedProfit: string | null
  expectedMarginPercent: string | null
  actualProfit: string | null
  actualMarginPercent: string | null
  progressPercent: string | null
  bac: string | null
  pv: string | null
  ev: string | null
  ac: string | null
  cpi: string | null
  spi: string | null
  etc: string | null
  eac: string | null
  vac: string | null
}

export interface WBSNode {
  id: string
  projectId: string
  parentId: string | null
  code: string
  name: string
  level: number
  manager: string | null
  status: WBSStatus
  plannedStart: string | null
  plannedFinish: string | null
  progressPercent: string
}

export interface WBSFinancialSummary {
  wbsNodeId: string
  authorized: string
  committed: string | null
  actualCost: string | null
  variance: string | null
}

export interface BudgetLine {
  id: string
  wbsNodeId: string | null
  economicCategoryId: string | null
  costCenterId: string | null
  fiscalPeriodId: string | null
  authorizedAmount: string
}

export interface Budget {
  id: string
  projectId: string
  version: 'BASELINE' | 'REVISED'
  status: 'ACTIVE' | 'SUPERSEDED'
  currencyCode: string
  previousBudgetId: string | null
  changeOrderId: string | null
  lines: BudgetLine[]
}

export interface BudgetSummary {
  authorized: string
  committed: string
  accrued: string
  paid: string
  available: string
}

export interface Forecast {
  bac: string
  pv: string | null
  ev: string | null
  ac: string
  cpi: string | null
  spi: string | null
  etc: string | null
  eac: string | null
  vac: string | null
}

export interface ChangeOrder {
  id: string
  projectId: string
  wbsNodeId: string | null
  reason: string
  scopeChange: string | null
  budgetChangeAmount: string
  contractChangeAmount: string
  scheduleChangeDays: number | null
  requestedBy: string
  approvedBy: string | null
  status: 'DRAFT' | 'SUBMITTED' | 'APPROVED' | 'REJECTED' | 'IMPLEMENTED' | 'CANCELLED'
}

export interface ProgressRecord {
  id: string
  projectId: string
  wbsNodeId: string | null
  recordDate: string
  plannedPercent: string
  actualPercent: string
  description: string | null
  responsible: string | null
  evidenceId: string | null
}
