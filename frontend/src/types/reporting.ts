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

export interface StatementRow {
  accountId: string
  accountCode: string
  accountName: string
  accountType: string
  balance: string
  [key: string]: unknown
}

export interface BalanceSheetReport {
  assets: StatementRow[]
  liabilities: StatementRow[]
  equity: StatementRow[]
  totalAssets: string
  totalLiabilities: string
  totalEquity: string
  currentEarnings: string
  totalEquityIncludingEarnings: string
  totalLiabilitiesAndEquity: string
  equationDelta: string
}

export interface IncomeStatementReport {
  revenue: StatementRow[]
  expenses: StatementRow[]
  totalRevenue: string
  totalExpenses: string
  netIncome: string
}

export interface GeneralLedgerRow {
  lineId: string
  documentId: string
  documentNumber: string
  postedAt: string | null
  documentStatus: string
  accountId: string
  accountCode: string
  accountName: string
  accountType: string
  scope: string
  projectId: string | null
  description: string | null
  debitAmount: string
  creditAmount: string
  [key: string]: unknown
}

export interface GeneralLedgerReport {
  rows: GeneralLedgerRow[]
  total: number
  offset: number
  limit: number
  totalDebit: string
  totalCredit: string
}

export interface CashFlowReport {
  operating: StatementRow[]
  investing: StatementRow[]
  financing: StatementRow[]
  unclassified: StatementRow[]
  totalOperating: string
  totalInvesting: string
  totalFinancing: string
  totalUnclassified: string
  netChangeInCash: string
}
