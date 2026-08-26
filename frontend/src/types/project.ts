export interface Company {
  id: string
  name: string
  code: string | null
  legalName: string | null
  functionalCurrencyCode: string | null
  country: string | null
  fiscalId: string | null
}

export interface Project {
  id: string
  companyId: string
  name: string
  code: string | null
  customerRef: string | null
  manager: string | null
  currencyCode: string | null
  costCenterId: string | null
  plannedStart: string | null
  plannedEnd: string | null
  actualEnd: string | null
  status: string
  description: string | null
}

export interface WBSNode {
  id: string
  projectId: string
  parentId: string | null
  code: string
  name: string
  level: number
  manager: string | null
  status: string
  plannedStart: string | null
  plannedFinish: string | null
  progressPercent: string
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
  evidenceRef: string | null
}
