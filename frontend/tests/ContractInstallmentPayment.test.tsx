import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

/**
 * ORDEN MAESTRA §20–§25: el formulario REAL de pago de una factura ligada a un
 * contrato de ejecución muestra el contexto contractual y genera los
 * `ContractPaymentAllocation` por FIFO. Sin este flujo, §72 dice "NOT DONE".
 */

const company = { id: 'c1', name: 'NEXORA GROUP', code: null, legalName: null, functionalCurrencyCode: 'HNL' }
const treasuryAccounts = [
  { id: 't-atl', companyId: 'c1', name: 'Banco Atlántida HNL', kind: 'BANK', institution: 'Atlántida', accountReference: null, currencyCode: 'HNL', glAccountId: 'gl1', status: 'ACTIVE', balance: '900000.00' },
]
const invoice = {
  id: 'inv1', supplierId: 's1', invoiceNumber: 'FAC-CON-1', scope: 'PROJECT', projectId: 'p1',
  currencyCode: 'HNL', amount: 50000, taxAmount: 0, amountPaid: 0, dueDate: '2026-08-31',
  status: 'APPROVED', supplierContractId: 'k1',
}
const schedule = {
  id: 'sch1', companyId: 'c1', supplierContractId: 'k1', projectId: 'p1', currencyCode: 'HNL',
  scheduleType: 'MONTHLY', totalScheduled: '250000.00', status: 'ACTIVE',
  installments: [
    { installmentId: 'i1', sequence: 1, periodYear: 2026, periodMonth: 7, periodLabel: 'Julio 2026', dueDate: '2026-07-31', scheduledAmount: '50000.00', retentionAmount: '0.00', netDue: '50000.00', paid: '0.00', remaining: '50000.00', status: 'OVERDUE' },
    { installmentId: 'i2', sequence: 2, periodYear: 2026, periodMonth: 8, periodLabel: 'Agosto 2026', dueDate: '2026-08-31', scheduledAmount: '50000.00', retentionAmount: '0.00', netDue: '50000.00', paid: '0.00', remaining: '50000.00', status: 'DUE' },
  ],
}
const summary = {
  contractValue: '250000.00', totalScheduledToDate: '100000.00', paidAccumulated: '0.00',
  contractBalance: '250000.00', overdueBalance: '50000.00', nextDuePeriod: 'Julio 2026',
  nextDueAmount: '50000.00', currencyCode: 'HNL',
}
const contracts = [
  { id: 'k1', companyId: 'c1', supplierId: 's1', projectId: 'p1', contractNumber: 'C-LAB-001', contractCategory: 'LABOR', scopeDescription: null, value: '250000.00', currencyCode: 'HNL', startDate: '2026-06-01', endDate: null, advancePercentage: '0.00', retentionPercentage: '0.00', paymentTerms: null, status: 'ACTIVE' },
]

describe('Contract installment payment (§20–§25)', () => {
  it('shows contractual context and FIFO allocation, and sends contractAllocations', async () => {
    let paymentPayload: Record<string, unknown> | null = null
    let fifoAmount: string | null = null

    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = init?.method ?? 'GET'
      if (url.includes('/auth/me')) return Promise.resolve({ ok: true, status: 200, json: async () => ({ id: 'u1', email: 'a@nexora.group', fullName: 'Admin', roles: ['Administrator'] }) } as Response)
      if (url.includes('/master-data/companies')) return Promise.resolve({ ok: true, status: 200, json: async () => [company] } as Response)
      if (url.includes('/master-data/accounts')) return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      if (url.includes('/treasury/accounts')) return Promise.resolve({ ok: true, status: 200, json: async () => treasuryAccounts } as Response)
      if (url.includes('/procurement/suppliers/contracts')) return Promise.resolve({ ok: true, status: 200, json: async () => contracts } as Response)
      if (url.includes('/procurement/suppliers')) return Promise.resolve({ ok: true, status: 200, json: async () => [{ id: 's1', companyId: 'c1', legalName: 'Constructora Aliada', status: 'ACTIVE' }] } as Response)
      if (url.includes('/contract-payments/by-contract/k1')) return Promise.resolve({ ok: true, status: 200, json: async () => schedule } as Response)
      if (url.includes('/contract-payments/schedules/sch1/summary')) return Promise.resolve({ ok: true, status: 200, json: async () => summary } as Response)
      if (url.includes('/contract-payments/schedules/sch1/fifo-preview')) {
        fifoAmount = JSON.parse(String(init?.body)).amount
        return Promise.resolve({ ok: true, status: 200, json: async () => [
          { installmentId: 'i1', periodLabel: 'Julio 2026', amountApplied: '50000.00' },
        ] } as Response)
      }
      if (url.includes('/ap/supplier-invoices/inv1/payments') && method === 'POST') {
        paymentPayload = JSON.parse(String(init?.body))
        return Promise.resolve({ ok: true, status: 201, json: async () => ({ id: 'pay1' }) } as Response)
      }
      if (url.includes('/ap/supplier-invoices/inv1')) return Promise.resolve({ ok: true, status: 200, json: async () => ({ ...invoice, status: 'PAID', amountPaid: 50000 }) } as Response)
      if (url.includes('/ap/supplier-invoices')) return Promise.resolve({ ok: true, status: 200, json: async () => [invoice] } as Response)
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }))

    render(renderApp('/finanzas/cuentas-por-pagar'))

    await userEvent.click(await screen.findByRole('button', { name: /pagar saldo/i }))

    // Contexto contractual visible dentro del pago.
    expect(await screen.findByText('C-LAB-001')).toBeInTheDocument()
    expect(screen.getByText('Mano de obra')).toBeInTheDocument()
    const context = screen.getByText('C-LAB-001').closest('.nx-contract-context') as HTMLElement
    expect(within(context).getAllByText('Julio 2026').length).toBeGreaterThan(0)
    expect(within(context).getAllByText('Agosto 2026').length).toBeGreaterThan(0)

    // Propuesta FIFO calculada con el monto del pago.
    await waitFor(() => expect(fifoAmount).toBe('50000'))
    expect(await within(context).findByText(/Asignación automática \(FIFO\)/)).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText(/cuenta pagadora/i), 't-atl')
    await userEvent.click(screen.getByRole('button', { name: /confirmar pago/i }))

    await waitFor(() =>
      expect(paymentPayload).toMatchObject({
        amount: '50000',
        contractAllocations: [{ installmentId: 'i1', amountApplied: '50000.00' }],
      }),
    )
  })
})
