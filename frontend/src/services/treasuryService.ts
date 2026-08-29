import { apiFetch } from './httpClient'
import type {
  GeneralExpense,
  Remittance,
  TreasuryAccount,
  TreasuryTransfer,
} from '../types/treasury'

export interface CreateTreasuryAccountPayload {
  companyId: string
  name: string
  kind: TreasuryAccount['kind']
  currencyCode: string
  glAccountId: string
  institution?: string | null
  accountReference?: string | null
}

export interface CreateRemittancePayload {
  companyId: string
  treasuryAccountId: string
  counterAccountId: string
  originType: 'CAPITAL_CONTRIBUTION' | 'FINANCING' | 'OTHER_INCOME'
  sender: string
  provider?: string | null
  channel?: string | null
  reference?: string | null
  currencyCode: string
  originalAmount: string
  fxRate?: string
  remittanceDate: string
  notes?: string | null
}

export interface CreateGeneralExpensePayload {
  companyId: string
  treasuryAccountId: string
  expenseAccountId: string
  scope: 'GENERAL' | 'PROJECT'
  projectId?: string | null
  category: string
  amount: string
  currencyCode: string
  expenseDate: string
  description: string
}

export interface CreateTransferPayload {
  companyId: string
  sourceTreasuryAccountId: string
  destinationTreasuryAccountId: string
  amount: string
  currencyCode: string
  transferDate: string
}

export interface CashClosing {
  id: string
  treasuryAccountId: string
  closingDate: string
  openingAmount: number
  expectedAmount: number
  countedAmount: number
  differenceAmount: number
  status: string
  accountingDocumentId: string | null
}

export interface BankStatement {
  id: string
  treasuryAccountId: string
  statementDate: string
  openingBalance: number
  closingBalance: number
  reference: string | null
}

export interface BankStatementLine {
  id: string
  bankStatementId: string
  lineDate: string
  description: string
  amount: number
  status: string
}

export interface ReconciliationMatch {
  id: string
  bankStatementLineId: string
  accountingDocumentId: string
  matchedAmount: number
  matchedByUserId: string
  matchedAt: string
}

export interface ReconciliationCandidate {
  accountingDocumentId: string
  documentNumber: string
  documentTypeCode: string
  description: string | null
  availableAmount: number
  exactMatch: boolean
}

export interface FundRestriction {
  id: string
  treasuryAccountId: string
  restrictedForProjectId: string | null
  amount: number
  description: string
  active: boolean
}

export interface TreasuryAvailability {
  treasuryAccountId: string
  balance: number
  reservedAmount: number
  availableAmount: number
}

type TreasuryAccountWire = Omit<TreasuryAccount, 'balance'> & { balance: number | string }
type RemittanceWire = Omit<Remittance, 'originalAmount' | 'fxRate' | 'baseAmount'> & {
  originalAmount: number | string
  fxRate: number | string
  baseAmount: number | string
}
type CashClosingWire = Omit<CashClosing, 'openingAmount' | 'expectedAmount' | 'countedAmount' | 'differenceAmount'> & {
  openingAmount: number | string
  expectedAmount: number | string
  countedAmount: number | string
  differenceAmount: number | string
}
type BankStatementWire = Omit<BankStatement, 'openingBalance' | 'closingBalance'> & {
  openingBalance: number | string
  closingBalance: number | string
}
type BankStatementLineWire = Omit<BankStatementLine, 'amount'> & { amount: number | string }
type FundRestrictionWire = Omit<FundRestriction, 'amount'> & { amount: number | string }
type TreasuryAvailabilityWire = Omit<TreasuryAvailability, 'balance' | 'reservedAmount' | 'availableAmount'> & {
  balance: number | string
  reservedAmount: number | string
  availableAmount: number | string
}

function normalizeTreasuryAccount(account: TreasuryAccountWire): TreasuryAccount {
  return { ...account, balance: Number(account.balance) }
}

function normalizeRemittance(item: RemittanceWire): Remittance {
  return {
    ...item,
    originalAmount: Number(item.originalAmount),
    fxRate: Number(item.fxRate),
    baseAmount: Number(item.baseAmount),
  }
}

function normalizeCashClosing(item: CashClosingWire): CashClosing {
  return {
    ...item,
    openingAmount: Number(item.openingAmount),
    expectedAmount: Number(item.expectedAmount),
    countedAmount: Number(item.countedAmount),
    differenceAmount: Number(item.differenceAmount),
  }
}

function normalizeStatement(item: BankStatementWire): BankStatement {
  return { ...item, openingBalance: Number(item.openingBalance), closingBalance: Number(item.closingBalance) }
}

function normalizeLine(item: BankStatementLineWire): BankStatementLine {
  return { ...item, amount: Number(item.amount) }
}

function normalizeRestriction(item: FundRestrictionWire): FundRestriction {
  return { ...item, amount: Number(item.amount) }
}

export const treasuryService = {
  listAccounts: async (companyId: string) =>
    (await apiFetch<TreasuryAccountWire[]>(`/treasury/accounts?companyId=${companyId}`)).map(
      normalizeTreasuryAccount,
    ),
  createAccount: async (payload: CreateTreasuryAccountPayload) =>
    normalizeTreasuryAccount(
      await apiFetch<TreasuryAccountWire>('/treasury/accounts', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    ),
  listRemittances: async (companyId: string, offset = 0, limit = 25) =>
    (await apiFetch<RemittanceWire[]>(
      `/treasury/remittances?companyId=${encodeURIComponent(companyId)}&offset=${offset}&limit=${limit}`,
    )).map(normalizeRemittance),
  createRemittance: (payload: CreateRemittancePayload, idempotencyKey: string) =>
    apiFetch<Remittance>('/treasury/remittances', {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify(payload),
    }),
  createGeneralExpense: (payload: CreateGeneralExpensePayload, idempotencyKey: string) =>
    apiFetch<GeneralExpense>('/treasury/general-expenses', {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify(payload),
    }),
  createTransfer: (payload: CreateTransferPayload, idempotencyKey: string) =>
    apiFetch<TreasuryTransfer>('/treasury/transfers', {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify(payload),
    }),

  listCashClosings: async (companyId: string) =>
    (await apiFetch<CashClosingWire[]>(`/treasury/cash-closings?companyId=${encodeURIComponent(companyId)}`)).map(normalizeCashClosing),
  createCashClosing: async (payload: {
    treasuryAccountId: string
    closingDate: string
    openingAmount: string
    expectedAmount: string
    countedAmount: string
  }) => normalizeCashClosing(await apiFetch<CashClosingWire>('/treasury/cash-closings', { method: 'POST', body: JSON.stringify(payload) })),
  approveCashClosing: async (closingId: string, differenceAccountId?: string) =>
    normalizeCashClosing(await apiFetch<CashClosingWire>(`/treasury/cash-closings/${closingId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ differenceAccountId: differenceAccountId || null }),
    })),

  listBankStatements: async (companyId: string) =>
    (await apiFetch<BankStatementWire[]>(`/treasury/bank-statements?companyId=${encodeURIComponent(companyId)}`)).map(normalizeStatement),
  createBankStatement: async (payload: {
    treasuryAccountId: string
    statementDate: string
    openingBalance: string
    closingBalance: string
    reference?: string
  }) => normalizeStatement(await apiFetch<BankStatementWire>('/treasury/bank-statements', { method: 'POST', body: JSON.stringify(payload) })),
  listBankStatementLines: async (statementId: string) =>
    (await apiFetch<BankStatementLineWire[]>(`/treasury/bank-statements/${statementId}/lines`)).map(normalizeLine),
  addBankStatementLine: async (statementId: string, payload: { lineDate: string; description: string; amount: string }) =>
    normalizeLine(await apiFetch<BankStatementLineWire>(`/treasury/bank-statements/${statementId}/lines`, { method: 'POST', body: JSON.stringify(payload) })),
  listReconciliationMatches: (lineId: string) => apiFetch<ReconciliationMatch[]>(`/treasury/bank-statement-lines/${lineId}/matches`),
  listReconciliationCandidates: async (lineId: string) =>
    (await apiFetch<Array<Omit<ReconciliationCandidate, 'availableAmount'> & { availableAmount: number | string }>>(`/treasury/bank-statement-lines/${lineId}/candidates`)).map((item) => ({ ...item, availableAmount: Number(item.availableAmount) })),
  matchReconciliationLine: (lineId: string, accountingDocumentId: string, matchedAmount: number) =>
    apiFetch<ReconciliationMatch>(`/treasury/bank-statement-lines/${lineId}/matches`, { method: 'POST', body: JSON.stringify({ accountingDocumentId, matchedAmount: String(matchedAmount) }) }),
  unmatchReconciliationLine: async (lineId: string) =>
    normalizeLine(await apiFetch<BankStatementLineWire>(`/treasury/bank-statement-lines/${lineId}/unmatch`, { method: 'POST' })),
  excludeReconciliationLine: async (lineId: string) =>
    normalizeLine(await apiFetch<BankStatementLineWire>(`/treasury/bank-statement-lines/${lineId}/exclude`, { method: 'POST' })),

  listFundRestrictions: async (companyId: string) =>
    (await apiFetch<FundRestrictionWire[]>(`/treasury/fund-restrictions?companyId=${encodeURIComponent(companyId)}`)).map(normalizeRestriction),
  createFundRestriction: async (payload: { treasuryAccountId: string; restrictedForProjectId?: string | null; amount: string; description: string }) =>
    normalizeRestriction(await apiFetch<FundRestrictionWire>('/treasury/fund-restrictions', { method: 'POST', body: JSON.stringify(payload) })),
  releaseFundRestriction: async (restrictionId: string) =>
    normalizeRestriction(await apiFetch<FundRestrictionWire>(`/treasury/fund-restrictions/${restrictionId}/release`, { method: 'POST' })),
  getAvailability: async (treasuryAccountId: string, projectId?: string) => {
    const suffix = projectId ? `?projectId=${encodeURIComponent(projectId)}` : ''
    const item = await apiFetch<TreasuryAvailabilityWire>(`/treasury/accounts/${treasuryAccountId}/availability${suffix}`)
    return { ...item, balance: Number(item.balance), reservedAmount: Number(item.reservedAmount), availableAmount: Number(item.availableAmount) }
  },
}