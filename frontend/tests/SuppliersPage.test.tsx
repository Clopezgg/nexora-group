import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(companies: unknown[], suppliers: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ id: 'u1', email: 'admin@nexora.group', fullName: 'Admin', roles: ['Administrator'] }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => companies } as Response)
      }
      if (url.includes('/procurement/suppliers')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => suppliers } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('SuppliersPage', () => {
  it('shows an honest empty state when there are no companies yet', async () => {
    stubFetch([], [])

    render(renderApp('/abastecimiento/proveedores'))

    expect(await screen.findByText(/configura una compañía primero/i)).toBeInTheDocument()
  })

  it('lists real suppliers for the active company, never fabricated rows', async () => {
    stubFetch(
      [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }],
      [
        {
          id: 's1',
          companyId: 'c1',
          legalName: 'Ferretería Nexora S.A.',
          tradeName: null,
          taxId: '08011999123456',
          email: null,
          phone: null,
          status: 'ACTIVE',
          classification: null,
        },
      ],
    )

    render(renderApp('/abastecimiento/proveedores'))

    expect(await screen.findByText('Ferretería Nexora S.A.')).toBeInTheDocument()
    expect(screen.getByText('08011999123456')).toBeInTheDocument()
  })
})
