import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(handlers: Record<string, unknown>) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            id: 'u1',
            email: 'admin@nexora.group',
            fullName: 'Admin',
            roles: ['Administrator'],
          }),
        } as Response)
      }
      for (const [fragment, body] of Object.entries(handlers)) {
        if (url.includes(fragment)) {
          return Promise.resolve({ ok: true, status: 200, json: async () => body } as Response)
        }
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }),
  )
}

const COMPANY = { id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }

describe('CustomersPage', () => {
  it('shows an honest empty state when there are no companies yet', async () => {
    stubFetch({ '/master-data/companies': [] })

    render(renderApp('/comercial/clientes'))

    expect(await screen.findByText(/configura una compañía primero/i)).toBeInTheDocument()
  })

  it('lists real customers for the active company, never fabricated rows', async () => {
    stubFetch({
      '/master-data/companies': [COMPANY],
      '/crm/customers': [
        {
          id: 'cu1',
          companyId: 'c1',
          legalName: 'Inversiones ABC',
          tradeName: null,
          taxId: '08011999999999',
          contactName: null,
          email: null,
          phone: null,
          address: null,
          status: 'ACTIVE',
        },
      ],
    })

    render(renderApp('/comercial/clientes'))

    expect(await screen.findByText('Inversiones ABC')).toBeInTheDocument()
    expect(screen.getByText('08011999999999')).toBeInTheDocument()
  })
})

describe('LeadsPage', () => {
  it('offers conversion only for a lead that has not been converted yet', async () => {
    stubFetch({
      '/master-data/companies': [COMPANY],
      '/crm/leads': [
        {
          id: 'l1',
          companyId: 'c1',
          name: 'Constructora Prospecto',
          contactName: 'Juan Perez',
          email: null,
          phone: null,
          source: 'REFERRAL',
          status: 'NEW',
          convertedCustomerId: null,
        },
        {
          id: 'l2',
          companyId: 'c1',
          name: 'Prospecto Convertido',
          contactName: null,
          email: null,
          phone: null,
          source: null,
          status: 'CONVERTED',
          convertedCustomerId: 'cu9',
        },
      ],
    })

    render(renderApp('/comercial/leads'))

    expect(await screen.findByText('Constructora Prospecto')).toBeInTheDocument()
    expect(screen.getByText('Prospecto Convertido')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /convertir a cliente/i })).toBeInTheDocument()
    expect(screen.getByText(/convertido a cliente/i)).toBeInTheDocument()
  })
})

describe('SalesContractsPage', () => {
  it('shows the real AR invoice reference for a billed contract instead of a Facturar action', async () => {
    stubFetch({
      '/master-data/companies': [COMPANY],
      '/master-data/accounts': [
        { id: 'a1', code: '4100', name: 'Ingresos', accountType: 'REVENUE', parentId: null, isPostable: true },
        { id: 'a2', code: '1200', name: 'CxC', accountType: 'ASSET', parentId: null, isPostable: true },
      ],
      '/crm/sales-contracts': [
        {
          id: 'sc1',
          companyId: 'c1',
          quotationId: 'q1',
          customerId: 'cu1',
          projectId: null,
          contractNumber: 'SC-001',
          scope: 'GENERAL',
          amount: '50000.00',
          currencyCode: 'HNL',
          startDate: '2026-02-01',
          status: 'BILLED',
          customerInvoiceId: 'inv-123456789',
        },
      ],
    })

    render(renderApp('/comercial/contratos'))

    expect(await screen.findByText('SC-001')).toBeInTheDocument()
    expect(screen.getByText(/facturado \(ar #inv-1234/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /facturar/i })).not.toBeInTheDocument()
  })
})
