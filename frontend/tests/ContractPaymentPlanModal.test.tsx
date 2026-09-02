import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import { ContractPaymentPlanModal } from '../src/features/procurement/ContractPaymentPlanModal'
import type { SupplierContract } from '../src/types/procurement'

const CONTRACT: SupplierContract = {
  id: 'k1', companyId: 'c1', supplierId: 's1', projectId: 'p1', contractNumber: '10101960',
  contractCategory: 'LABOR', scopeDescription: null, value: '1500000.00', currencyCode: 'HNL',
  startDate: '2026-08-01', endDate: null, advancePercentage: '0.00', advanceAmount: '50000.00',
  advanceDueDate: '2026-08-22', retentionPercentage: '0.00', paymentTerms: null,
  paymentTermsType: 'MONTHLY', status: 'ACTIVE',
}

const mkInst = (o: Record<string, unknown>) => ({
  installmentId: '', sequence: 0, installmentKind: 'REGULAR', periodYear: 2026, periodMonth: 9,
  periodLabel: 'Septiembre 2026', dueDate: '2026-09-01', scheduledAmount: '207142.85',
  retentionAmount: '0.00', netDue: '207142.85', paid: '0.00', remaining: '207142.85',
  status: 'UPCOMING', regularNumber: 1, regularCount: 7, ...o,
})
const months = [9, 10, 11, 12, 1, 2, 3]
const schedule = {
  id: 'sch1', companyId: 'c1', supplierContractId: 'k1', projectId: 'p1', currencyCode: 'HNL',
  scheduleType: 'MONTHLY', dueDay: 1, totalScheduled: '1500000.00', status: 'ACTIVE',
  installments: [
    mkInst({ installmentId: 'adv', sequence: 1, installmentKind: 'ADVANCE', periodLabel: 'Anticipo', periodMonth: 8, dueDate: '2026-08-22', scheduledAmount: '50000.00', netDue: '50000.00', remaining: '50000.00', regularNumber: null, regularCount: null, status: 'DUE' }),
    ...months.map((m, i) =>
      mkInst({
        installmentId: `r${i + 1}`, sequence: i + 2, periodMonth: m,
        periodYear: m >= 9 ? 2026 : 2027,
        dueDate: `${m >= 9 ? 2026 : 2027}-${String(m).padStart(2, '0')}-01`,
        scheduledAmount: i === 6 ? '207142.90' : '207142.85',
        netDue: i === 6 ? '207142.90' : '207142.85',
        remaining: i === 6 ? '207142.90' : '207142.85',
        regularNumber: i + 1,
      }),
    ),
  ],
}
const summary = {
  contractValue: '1500000.00', totalScheduledToDate: '0.00', paidAccumulated: '0.00',
  contractBalance: '1500000.00', overdueBalance: '0.00', nextDuePeriod: 'Anticipo',
  nextDueAmount: '50000.00', currencyCode: 'HNL', advanceScheduled: '50000.00',
  regularScheduled: '1450000.00', totalContractualScheduled: '1500000.00', advancePaid: '0.00',
  advanceRemaining: '50000.00', retentionOutstanding: '0.00',
}

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
}

describe('ContractPaymentPlanModal — plan de 10101960 (§3/§25/§26)', () => {
  it('muestra el anticipo + 7 mensualidades y el desglose exacto', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        const ok = (b: unknown) => Promise.resolve({ ok: true, status: 200, json: async () => b } as Response)
        if (url.includes('/contract-payments/by-contract/k1')) return ok(schedule)
        if (url.includes('/contract-payments/schedules/sch1/summary')) return ok(summary)
        return ok([])
      }),
    )

    render(wrap(<ContractPaymentPlanModal contract={CONTRACT} currencyCode="HNL" onClose={() => {}} />))

    const dialog = await screen.findByRole('dialog')
    // Desglose (§25).
    expect((await within(dialog).findByText('Anticipo programado')).closest('div')!).toHaveTextContent('L 50,000.00')
    expect(within(dialog).getByText('Base regular').closest('div')!).toHaveTextContent('L 1,450,000.00')
    expect(within(dialog).getByText('Total programado').closest('div')!).toHaveTextContent('L 1,500,000.00')
    // Anticipo es 1 fila; 7 mensualidades (§6 — no "Cuota 1 de 8").
    expect(within(dialog).getAllByText('Mensualidad').length).toBe(7)
    expect(within(dialog).getAllByText('Anticipo').length).toBeGreaterThan(0)
    // La última mensualidad absorbe el redondeo: 207,142.90.
    expect(within(dialog).getAllByText('L 207,142.90').length).toBeGreaterThan(0)
    expect(within(dialog).getAllByText('L 207,142.85').length).toBeGreaterThanOrEqual(6)
  })

  it('corrige el plan: previsualiza ANTES/DESPUÉS y exige un motivo (§9/§10)', async () => {
    const rebuildCalls: unknown[] = []
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const ok = (b: unknown) => Promise.resolve({ ok: true, status: 200, json: async () => b } as Response)
        if (url.includes('/contract-payments/by-contract/k1')) return ok(schedule)
        if (url.includes('/contract-payments/schedules/sch1/summary')) return ok(summary)
        if (url.includes('/contract-payments/schedules/sch1/rebuild/preview')) {
          return ok({
            blocked: false,
            blockedReason: null,
            before: { totalScheduled: '1500000.00', installments: [
              { kind: 'REGULAR', periodLabel: 'Septiembre 2026', dueDate: '2026-09-30', scheduledAmount: '214285.71', retentionAmount: '0.00', netDue: '214285.71' },
            ] },
            after: { totalScheduled: '1500000.00', installments: [
              { kind: 'ADVANCE', periodLabel: 'Anticipo', dueDate: '2026-08-22', scheduledAmount: '50000.00', retentionAmount: '0.00', netDue: '50000.00' },
              { kind: 'REGULAR', periodLabel: 'Septiembre 2026', dueDate: '2026-09-01', scheduledAmount: '207142.85', retentionAmount: '0.00', netDue: '207142.85' },
            ] },
          })
        }
        if (url.includes('/contract-payments/schedules/sch1/rebuild')) {
          rebuildCalls.push(JSON.parse(String(init?.body)))
          return ok(schedule)
        }
        return ok([])
      }),
    )
    const user = userEvent.setup()
    render(wrap(<ContractPaymentPlanModal contract={CONTRACT} currencyCode="HNL" onClose={() => {}} />))

    const dialog = await screen.findByRole('dialog')
    await user.click(await within(dialog).findByRole('button', { name: /corregir plan de pagos/i }))
    await user.click(await within(dialog).findByRole('button', { name: /previsualizar cambios/i }))

    expect(await within(dialog).findByText('ANTES · total L 1,500,000.00')).toBeInTheDocument()
    expect(within(dialog).getByText('DESPUÉS · total L 1,500,000.00')).toBeInTheDocument()

    const apply = within(dialog).getByRole('button', { name: /aplicar corrección/i })
    expect(apply).toBeDisabled()
    await user.type(within(dialog).getByPlaceholderText(/mínimo 10 caracteres/i), 'Plan legacy sin anticipo')
    expect(apply).toBeEnabled()
    await user.click(apply)

    expect(rebuildCalls).toHaveLength(1)
    expect(rebuildCalls[0]).toMatchObject({ reason: 'Plan legacy sin anticipo', regularMonths: 7 })
  })
})
