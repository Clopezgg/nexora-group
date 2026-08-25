import { afterEach, describe, expect, it, vi } from 'vitest'
import { apService, arService } from '../src/services/apArService'
import { treasuryService } from '../src/services/treasuryService'

const paymentPayload = {
  treasuryAccountId: 'treasury-1',
  amount: '25.00',
  paymentDate: '2026-08-24',
}

const receiptPayload = {
  treasuryAccountId: 'treasury-1',
  amount: '25.00',
  receiptDate: '2026-08-24',
}

const remittancePayload = {
  companyId: 'company-1',
  treasuryAccountId: 'treasury-1',
  counterAccountId: 'account-1',
  sender: 'Sender',
  currencyCode: 'HNL',
  originalAmount: '25.00',
  remittanceDate: '2026-08-24',
}

const expensePayload = {
  companyId: 'company-1',
  treasuryAccountId: 'treasury-1',
  expenseAccountId: 'account-1',
  category: 'office',
  amount: '25.00',
  currencyCode: 'HNL',
  expenseDate: '2026-08-24',
  description: 'Paper',
}

const transferPayload = {
  companyId: 'company-1',
  sourceTreasuryAccountId: 'treasury-1',
  destinationTreasuryAccountId: 'treasury-2',
  amount: '25.00',
  currencyCode: 'HNL',
  transferDate: '2026-08-24',
}

describe('financial service idempotency', () => {
  afterEach(() => vi.unstubAllGlobals())

  it.each([
    {
      name: 'supplier payment',
      payload: paymentPayload,
      invoke: (key: string) => apService.pay('supplier-invoice-1', paymentPayload, key),
    },
    {
      name: 'customer receipt',
      payload: receiptPayload,
      invoke: (key: string) => arService.collect('customer-invoice-1', receiptPayload, key),
    },
    {
      name: 'remittance',
      payload: remittancePayload,
      invoke: (key: string) => treasuryService.createRemittance(remittancePayload, key),
    },
    {
      name: 'general expense',
      payload: expensePayload,
      invoke: (key: string) => treasuryService.createGeneralExpense(expensePayload, key),
    },
    {
      name: 'treasury transfer',
      payload: transferPayload,
      invoke: (key: string) => treasuryService.createTransfer(transferPayload, key),
    },
  ])('keeps one nonempty key and payload across a $name retry', async ({ payload, invoke }) => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({}),
    } as Response)
    vi.stubGlobal('fetch', fetchMock)
    const intentKey = crypto.randomUUID()

    await invoke(intentKey)
    await invoke(intentKey)

    expect(intentKey).not.toBe('')
    expect(fetchMock).toHaveBeenCalledTimes(2)
    for (const [, options] of fetchMock.mock.calls as [string, RequestInit][]) {
      const headers = new Headers(options.headers)
      expect(headers.get('Idempotency-Key')).toBe(intentKey)
      expect(headers.get('Content-Type')).toBe('application/json')
      expect(options.body).toBe(JSON.stringify(payload))
    }
  })
})
