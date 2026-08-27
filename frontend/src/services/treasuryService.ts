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

type TreasuryAccountWire = Omit<TreasuryAccount, 'balance'> & { balance: number | string }
type RemittanceWire = Omit<Remittance, 'originalAmount' | 'fxRate' | 'baseAmount'> & {
  originalAmount: number | string
  fxRate: number | string
  baseAmount: number | string
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
}
