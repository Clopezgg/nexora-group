export interface CashFlowPoint {
  period: string
  income: string
  expense: string
}

export interface ScopeAmount {
  scope: 'CENTRAL' | 'GENERAL' | 'PROJECT'
  amount: string
}

export interface DashboardSummary {
  treasuryBalance: string
  periodIncome: string
  periodExpense: string
  activeProjects: number
  pendingApprovals: number
  overduePayables: number
  overduePayablesAmount: string
  receivablesOutstanding: string
  cashFlow: CashFlowPoint[]
  expensesByScope: ScopeAmount[]
  currency: string
  fiscalPeriodLabel: string | null
  fiscalPeriodStatus: string | null
  fiscalPeriodStart: string | null
  fiscalPeriodEnd: string | null
}
