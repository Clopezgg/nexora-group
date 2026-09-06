import { afterEach, describe, expect, it, vi } from 'vitest'
import { apService, arService } from '../src/services/apArService'
import { apMetricsService } from '../src/services/financialControlService'
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

  it('fetches AP aging metrics from /financial-control/ap-metrics (ORDEN MAESTRA §19)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        asOf: '2026-09-03',
        apOutstanding: '2100.00',
        aging: { current: '500.00', '1_30': '700.00', '31_60': '0', '61_90': '900.00', over_90: '0' },
      }),
    } as Response)
    vi.stubGlobal('fetch', fetchMock)

    const result = await apMetricsService.get('company-1')

    const [url] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/financial-control/ap-metrics?companyId=company-1')
    expect(result.apOutstanding).toBe('2100.00')
    expect(result.aging['61_90']).toBe('900.00')
  })

  it('sends the supplier-invoice payment plan as a PUT with installments', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] } as Response)
    vi.stubGlobal('fetch', fetchMock)

    await apService.setPaymentPlan('inv-1', [
      { dueDate: '2026-02-10', amount: '400.00' },
      { dueDate: '2026-03-10', amount: '750.00' },
    ])

    const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toContain('/ap/supplier-invoices/inv-1/payment-plan')
    expect(options.method).toBe('PUT')
    expect(JSON.parse(String(options.body))).toEqual({
      installments: [
        { dueDate: '2026-02-10', amount: '400.00' },
        { dueDate: '2026-03-10', amount: '750.00' },
      ],
    })
  })
})
