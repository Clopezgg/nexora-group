import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

const COMPANY = { id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }
const SUPPLIER = {
  id: 's1',
  companyId: 'c1',
  legalName: 'Proveedor Estructuras S.A.',
  tradeName: null,
  taxId: null,
  email: null,
  phone: null,
  status: 'ACTIVE',
  classification: null,
}
const RFQ = { id: 'rfq1', rfqNumber: 'RFQ-2026-000001', purchaseRequisitionId: null, dueDate: null, status: 'SENT' }
const QUOTATION = {
  id: 'q1',
  requestForQuotationId: 'rfq1',
  supplierId: 's1',
  currencyCode: 'HNL',
  status: 'RECEIVED',
  total: '1000.00',
  deliveryDays: 15,
  paymentTerms: '50% anticipo',
  validUntil: '2026-06-01',
  notes: null,
  lines: [],
}

function stubFetch(overrides: {
  rfqs?: unknown[]
  quotations?: unknown[]
  onCreatePO?: () => void
}) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      const method = init?.method ?? 'GET'
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ id: 'u1', email: 'admin@nexora.group', fullName: 'Admin', roles: ['Administrator'] }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [COMPANY] } as Response)
      }
      if (url.includes('/procurement/suppliers') && !url.includes('contracts')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [SUPPLIER] } as Response)
      }
      if (url.includes('/purchase-orders/from-quotation') && method === 'POST') {
        overrides.onCreatePO?.()
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({ id: 'po1', poNumber: 'PO-2026-000001', status: 'DRAFT' }),
        } as Response)
      }
      if (url.match(/\/procurement\/rfqs\/[^/?]+\/quotations$/)) {
        return Promise.resolve({ ok: true, status: 200, json: async () => overrides.quotations ?? [QUOTATION] } as Response)
      }
      if (url.includes('/procurement/rfqs')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => overrides.rfqs ?? [RFQ] } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }),
  )
}

describe('BidComparisonPage', () => {
  it('shows an honest empty state when there are no RFQs yet', async () => {
    stubFetch({ rfqs: [] })

    render(renderApp('/abastecimiento/comparativos'))

    expect(await screen.findByText(/aún no hay rfq/i)).toBeInTheDocument()
  })

  it('lists real RFQs and shows the quotation comparison for the selected one', async () => {
    stubFetch({})

    render(renderApp('/abastecimiento/comparativos'))

    expect(await screen.findByText('RFQ-2026-000001')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /comparar/i }))

    expect(await screen.findByText(/1000\.00/)).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.getByText('50% anticipo')).toBeInTheDocument()
  })

  it('selects a winning quotation and creates a real purchase order from it', async () => {
    const onCreatePO = vi.fn()
    stubFetch({ onCreatePO })

    render(renderApp('/abastecimiento/comparativos'))
    await userEvent.click(await screen.findByRole('button', { name: /comparar/i }))
    await screen.findByText(/1000\.00/)
    await userEvent.click(screen.getByRole('button', { name: /seleccionar ganadora/i }))

    expect(onCreatePO).toHaveBeenCalled()
    expect(await screen.findByText(/po-2026-000001/i)).toBeInTheDocument()
  })
})
