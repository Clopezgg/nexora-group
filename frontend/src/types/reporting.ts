export interface TrialBalanceRow {
  accountCode: string
  accountName: string
  debitBalance: string
  creditBalance: string
  [key: string]: unknown
}

export interface TrialBalanceReport {
  rows: TrialBalanceRow[]
  totalDebit: string
  totalCredit: string
}

export interface BudgetVsActualReport {
  authorized: string
  committed: string
  accrued: string
  paid: string
  available: string
}
