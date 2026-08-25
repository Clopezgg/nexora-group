import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(companies: unknown[], assets: unknown[]) {
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
      if (url.includes('/master-data/accounts')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      }
      if (url.includes('/assets')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => assets } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('FixedAssetsPage', () => {
  it('shows an honest empty state when there are no companies yet', async () => {
    stubFetch([], [])

    render(renderApp('/finanzas/activos'))

    expect(await screen.findByText(/configura una compañía primero/i)).toBeInTheDocument()
  })

  it('lists real fixed assets for the active company, never fabricated rows', async () => {
    stubFetch(
      [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }],
      [
        {
          id: 'a1',
          companyId: 'c1',
          category: 'Maquinaria pesada',
          name: 'Excavadora CAT 320',
          acquisitionDate: '2026-01-01',
          cost: '12000.00',
          currencyCode: 'HNL',
          usefulLifeMonths: 12,
          salvageValue: '0.00',
          location: null,
          responsible: null,
          status: 'ACTIVE',
          scope: 'GENERAL',
          projectId: null,
          costCenterId: null,
          depreciationExpenseAccountId: 'acc-1',
          accumulatedDepreciationAccountId: 'acc-2',
        },
      ],
    )

    render(renderApp('/finanzas/activos'))

    expect(await screen.findByText('Excavadora CAT 320')).toBeInTheDocument()
    expect(screen.getByText('HNL 12000.00')).toBeInTheDocument()
  })
})
