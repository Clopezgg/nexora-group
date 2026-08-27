export interface CashFlowPoint {
  period: string
  income: number
  expense: number
}

export interface ScopeAmount {
  scope: 'CENTRAL' | 'GENERAL' | 'PROJECT'
  amount: number
}

export interface DashboardSummary {
  treasuryBalance: number
  periodIncome: number
  periodExpense: number
  activeProjects: number
  pendingApprovals: number
  overduePayables: number
  overduePayablesAmount: number
  receivablesOutstanding: number
  cashFlow: CashFlowPoint[]
  expensesByScope: ScopeAmount[]
  currency: string
}
