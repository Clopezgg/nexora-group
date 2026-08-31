import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(companies: unknown[], trialBalance: unknown) {
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
      if (url.includes('/reports/trial-balance')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => trialBalance } as Response)
      }
      if (url.includes('/context')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ activeProjectId: null, activeProjectName: null }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('TrialBalancePage', () => {
  it('shows an honest empty state when there are no companies yet', async () => {
    stubFetch([], { rows: [], totalDebit: '0', totalCredit: '0' })

    render(renderApp('/control/reportes'))

    expect(await screen.findByText(/configura una compañía primero/i)).toBeInTheDocument()
  })

  it('loads and displays a real trial balance from the API, debits equal credits', async () => {
    stubFetch(
      [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }],
      {
        rows: [
          { accountId: 'acc-6000', accountCode: '6000', accountName: 'Gastos', debitBalance: '100.00', creditBalance: '0' },
          { accountId: 'acc-1000', accountCode: '1000', accountName: 'Caja', debitBalance: '0', creditBalance: '100.00' },
        ],
        totalDebit: '100.00',
        totalCredit: '100.00',
      },
    )

    render(renderApp('/control/reportes'))

    expect(await screen.findByText('Gastos')).toBeInTheDocument()
    expect(screen.getByText('Caja')).toBeInTheDocument()
    expect(screen.getByText(/Total débito: L 100.00 — Total crédito: L 100.00/)).toBeInTheDocument()
  })
})
