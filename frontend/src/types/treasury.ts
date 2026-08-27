export interface TreasuryAccount {
  id: string
  companyId: string
  name: string
  kind: 'BANK' | 'CASH' | 'OTHER'
  institution: string | null
  accountReference: string | null
  currencyCode: string
  glAccountId: string
  status: string
  balance: number
}

export interface Remittance {
  id: string
  companyId: string
  treasuryAccountId: string
  sender: string
  provider: string | null
  channel: string | null
  reference: string | null
  currencyCode: string
  originalAmount: number
  fxRate: number
  baseAmount: number
  remittanceDate: string
  accountingDocumentId: string
}

export interface GeneralExpense {
  id: string
  companyId: string
  treasuryAccountId: string
  category: string
  amount: number
  expenseDate: string
  accountingDocumentId: string
}

export interface TreasuryTransfer {
  id: string
  sourceTreasuryAccountId: string
  destinationTreasuryAccountId: string
  amount: number
  transferDate: string
  accountingDocumentId: string
}
