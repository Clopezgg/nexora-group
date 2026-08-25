import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(companies: unknown[], workers: unknown[]) {
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
      if (url.includes('/workforce/workers')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => workers } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('WorkersPage', () => {
  it('shows an honest empty state when there are no companies yet', async () => {
    stubFetch([], [])

    render(renderApp('/recursos/personal'))

    expect(await screen.findByText(/configura una compañía primero/i)).toBeInTheDocument()
  })

  it('reloads Workers from the real API and never fabricates rows', async () => {
    stubFetch(
      [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }],
      [
        {
          id: 'w1',
          companyId: 'c1',
          fullName: 'Juan Pérez',
          roleTitle: 'Albañil',
          standardHourlyRate: '125.50',
          active: true,
        },
      ],
    )

    render(renderApp('/recursos/personal'))

    expect(await screen.findByText('Juan Pérez')).toBeInTheDocument()
    expect(screen.getByText('Albañil')).toBeInTheDocument()
    expect(screen.getByText('125.50')).toBeInTheDocument()
  })
})
