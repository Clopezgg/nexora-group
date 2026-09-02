import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

/**
 * CORRECTIVA §30-§37: el formulario REAL de pago de una factura ligada a un
 * contrato de ejecución muestra el contexto contractual, asigna el pago a las
 * cuotas del plan y NUNCA registra un pago contractual sin asignación (§34).
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
const inst = (over: Record<string, unknown>) => ({
  installmentId: '', sequence: 0, installmentKind: 'REGULAR', periodYear: 2026, periodMonth: 7,
  periodLabel: 'Julio 2026', dueDate: '2026-07-01', scheduledAmount: '50000.00',
  retentionAmount: '0.00', netDue: '50000.00', paid: '0.00', remaining: '50000.00',
  status: 'OVERDUE', regularNumber: 1, regularCount: 2, ...over,
})
const schedule = {
  id: 'sch1', companyId: 'c1', supplierContractId: 'k1', projectId: 'p1', currencyCode: 'HNL',
  scheduleType: 'MONTHLY', dueDay: 1, totalScheduled: '250000.00', status: 'ACTIVE',
  installments: [
    inst({ installmentId: 'i1', sequence: 1, regularNumber: 1 }),
    inst({ installmentId: 'i2', sequence: 2, periodMonth: 8, periodLabel: 'Agosto 2026', dueDate: '2026-08-01', status: 'DUE', regularNumber: 2 }),
  ],
}
const summary = {
  contractValue: '250000.00', totalScheduledToDate: '100000.00', paidAccumulated: '0.00',
  contractBalance: '250000.00', overdueBalance: '50000.00', nextDuePeriod: 'Julio 2026',
  nextDueAmount: '50000.00', currencyCode: 'HNL', advanceScheduled: '0.00', regularScheduled: '250000.00',
  totalContractualScheduled: '250000.00', advancePaid: '0.00', advanceRemaining: '0.00', retentionOutstanding: '0.00',
}
const contracts = [
  { id: 'k1', companyId: 'c1', supplierId: 's1', projectId: 'p1', contractNumber: 'C-LAB-001', contractCategory: 'LABOR', scopeDescription: null, value: '250000.00', currencyCode: 'HNL', startDate: '2026-06-01', endDate: null, advancePercentage: '0.00', advanceAmount: null, advanceDueDate: null, retentionPercentage: '0.00', paymentTerms: null, paymentTermsType: 'MONTHLY', status: 'ACTIVE' },
]
const suppliers = [{ id: 's1', companyId: 'c1', legalName: 'Lester Rivas', status: 'ACTIVE', partyRole: 'CONTRACTOR' }]

describe('Contract installment payment (§30-§37)', () => {
  it('asigna íntegramente al plan, usa terminología de contratista y envía contractAllocations', async () => {
    let paymentPayload: Record<string, unknown> | null = null

    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = init?.method ?? 'GET'
      const ok = (b: unknown) => Promise.resolve({ ok: true, status: 200, json: async () => b } as Response)
      if (url.includes('/auth/me')) return ok({ id: 'u1', email: 'a@nexora.group', fullName: 'Admin', roles: ['Administrator'] })
      if (url.includes('/master-data/companies')) return ok([company])
      if (url.includes('/master-data/accounts')) return ok([])
      if (url.includes('/treasury/accounts')) return ok(treasuryAccounts)
      if (url.includes('/procurement/suppliers/contracts')) return ok(contracts)
      if (url.includes('/procurement/suppliers')) return ok(suppliers)
      if (url.includes('/contract-payments/by-contract/k1')) return ok(schedule)
      if (url.includes('/contract-payments/schedules/sch1/summary')) return ok(summary)
      if (url.includes('/ap/supplier-invoices/inv1/payments') && method === 'POST') {
        paymentPayload = JSON.parse(String(init?.body))
        return Promise.resolve({ ok: true, status: 201, json: async () => ({ id: 'pay1' }) } as Response)
      }
      if (url.includes('/ap/supplier-invoices/inv1')) return ok({ ...invoice, status: 'PAID', amountPaid: 50000 })
      if (url.includes('/ap/supplier-invoices')) return ok([invoice])
      return ok([])
    }))

    render(renderApp('/finanzas/cuentas-por-pagar'))

    await userEvent.click(await screen.findByRole('button', { name: /pagar saldo/i }))

    const context = (await screen.findByText('C-LAB-001')).closest('.nx-contract-context') as HTMLElement
    // Terminología de contratista (§37).
    expect(within(context).getByText(/Registrar pago a contratista/i)).toBeInTheDocument()
    // NO existe el fallback "se registrará sin asignación" (§34).
    expect(screen.queryByText(/sin asignación a cuotas contractuales/i)).not.toBeInTheDocument()
    // Asignación del pago visible.
    expect(await within(context).findByText(/Asignación del pago/i)).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText(/cuenta pagadora/i), 't-atl')
    await userEvent.click(screen.getByRole('button', { name: /confirmar pago/i }))

    await waitFor(() =>
      expect(paymentPayload).toMatchObject({
        amount: '50000',
        contractAllocations: [{ installmentId: 'i1', amountApplied: '50000.00' }],
      }),
    )
  })

  it('bloquea "Confirmar" cuando el monto no puede asignarse al plan (§34)', async () => {
    const smallSchedule = {
      ...schedule,
      installments: [inst({ installmentId: 'i1', sequence: 1, scheduledAmount: '10000.00', netDue: '10000.00', remaining: '10000.00' })],
    }
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      const ok = (b: unknown) => Promise.resolve({ ok: true, status: 200, json: async () => b } as Response)
      if (url.includes('/auth/me')) return ok({ id: 'u1', email: 'a@nexora.group', fullName: 'Admin', roles: ['Administrator'] })
      if (url.includes('/master-data/companies')) return ok([company])
      if (url.includes('/treasury/accounts')) return ok(treasuryAccounts)
      if (url.includes('/procurement/suppliers/contracts')) return ok(contracts)
      if (url.includes('/procurement/suppliers')) return ok(suppliers)
      if (url.includes('/contract-payments/by-contract/k1')) return ok(smallSchedule)
      if (url.includes('/contract-payments/schedules/sch1/summary')) return ok(summary)
      if (url.includes('/ap/supplier-invoices/inv1')) return ok(invoice)
      if (url.includes('/ap/supplier-invoices')) return ok([invoice])
      return ok([])
    }))

    render(renderApp('/finanzas/cuentas-por-pagar'))
    await userEvent.click(await screen.findByRole('button', { name: /pagar saldo/i }))
    await screen.findByText('C-LAB-001')
    await userEvent.selectOptions(screen.getByLabelText(/cuenta pagadora/i), 't-atl')

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /confirmar pago/i })).toBeDisabled(),
    )
    expect(screen.getAllByText(/no puede asignarse íntegramente al plan/i).length).toBeGreaterThan(0)
  })
})
