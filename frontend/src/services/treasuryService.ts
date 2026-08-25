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
  kind: string
  currencyCode: string
  glAccountId: string
}

export interface CreateRemittancePayload {
  companyId: string
  treasuryAccountId: string
  counterAccountId: string
  sender: string
  currencyCode: string
  originalAmount: string
  remittanceDate: string
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

function normalizeTreasuryAccount(account: TreasuryAccountWire): TreasuryAccount {
  return { ...account, balance: Number(account.balance) }
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
  createRemittance: (payload: CreateRemittancePayload) =>
    apiFetch<Remittance>('/treasury/remittances', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createGeneralExpense: (payload: CreateGeneralExpensePayload) =>
    apiFetch<GeneralExpense>('/treasury/general-expenses', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createTransfer: (payload: CreateTransferPayload) =>
    apiFetch<TreasuryTransfer>('/treasury/transfers', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
