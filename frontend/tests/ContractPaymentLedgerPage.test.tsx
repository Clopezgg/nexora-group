import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ContractPaymentLedgerPage } from '../src/features/finance/ContractPaymentLedgerPage'

vi.mock('../src/hooks/useActiveCompany', () => ({
  useActiveCompany: () => ({
    companies: [{ id: 'c1', name: 'Nexora', functionalCurrencyCode: 'HNL' }],
    activeCompanyId: 'c1',
    activeCompany: { id: 'c1', name: 'Nexora', functionalCurrencyCode: 'HNL' },
    setActiveCompanyId: vi.fn(),
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  }),
}))

const installment = (overrides: Record<string, unknown>) => ({
  installmentId: 'i1', sequence: 1, installmentKind: 'REGULAR', periodYear: 2026,
  periodMonth: 9, periodLabel: 'Septiembre 2026', dueDate: '2026-09-30',
  scheduledAmount: '207142.85', retentionAmount: '0.00', netDue: '207142.85',
  paid: '0.00', remaining: '207142.85', status: 'DUE', regularNumber: 1,
  regularCount: 7, payableNow: true, paymentBlockedReason: null,
  contractBalanceAfter: '1242857.15', ...overrides,
})

describe('ContractPaymentLedgerPage', () => {
  it('expone acciones ejecutables sólo para la cuota pagable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      let body: unknown = []
      if (url.includes('/reports/contract-payment-ledger')) body = {
        companyId: 'c1', asOf: '2026-09-10', totalContractValue: '1500000.00',
        totalPaidAccumulated: '50000.00', totalContractBalance: '1450000.00',
        entries: [{
          scheduleId: 'sch1', supplierContractId: 'ctr1', contractNumber: '10101960',
          supplierLegalName: 'Constructora Uno', projectId: 'p1', currencyCode: 'HNL',
          contractValue: '1500000.00', scheduledToDate: '257142.85',
          paidAccumulated: '50000.00', contractBalance: '1450000.00', overdueBalance: '0.00',
          installments: [
            installment({ installmentId: 'adv', sequence: 1, installmentKind: 'ADVANCE', periodLabel: 'Anticipo', paid: '50000.00', remaining: '0.00', status: 'PAID', payableNow: false, paymentBlockedReason: 'La cuota ya está pagada.' }),
            installment({ installmentId: 'sep', sequence: 2 }),
            installment({ installmentId: 'oct', sequence: 3, periodMonth: 10, periodLabel: 'Octubre 2026', status: 'UPCOMING', payableNow: false, paymentBlockedReason: 'La cuota pertenece a un período futuro.' }),
          ],
          allocations: [],
        }],
      }
      if (url.includes('/ap/supplier-invoices')) body = [{
        id: 'inv1', supplierId: 's1', invoiceNumber: 'SEP-2026', scope: 'PROJECT',
        projectId: 'p1', currencyCode: 'HNL', amount: '207142.85', taxAmount: '0.00',
        amountPaid: '0.00', dueDate: '2026-09-30', status: 'APPROVED',
        supplierContractId: 'ctr1', contractInstallmentId: 'sep',
      }]
      if (url.includes('/treasury/accounts')) body = [{
        id: 'bank1', companyId: 'c1', name: 'Banco', kind: 'BANK', currencyCode: 'HNL',
        status: 'ACTIVE', glAccountId: 'gl1',
      }]
      return Promise.resolve({ ok: true, status: 200, json: async () => body } as Response)
    }))
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

    render(
      <QueryClientProvider client={client}>
        <ContractPaymentLedgerPage />
      </QueryClientProvider>,
    )

    expect(await screen.findByRole('button', { name: 'Pagar Septiembre 2026' })).toBeEnabled()
    expect(screen.getByRole('button', { name: 'Liquidar Septiembre 2026' })).toBeEnabled()
    expect(screen.getAllByText('Bloqueada')).toHaveLength(2)
  })
})
