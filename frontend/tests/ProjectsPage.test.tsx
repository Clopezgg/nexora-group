import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(routes: Record<string, unknown>) {
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
      for (const [fragment, body] of Object.entries(routes)) {
        if (url.includes(fragment)) {
          return Promise.resolve({ ok: true, status: 200, json: async () => body } as Response)
        }
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('ProjectsPage', () => {
  it('explains that a company is required when there are none (no fabricated data)', async () => {
    stubFetch({ '/master-data/companies': [] })

    render(renderApp('/proyectos'))

    expect(await screen.findByText('Sin compañía')).toBeInTheDocument()
    expect(screen.getByText('Configura una compañía antes de crear proyectos.')).toBeInTheDocument()
    expect(screen.queryByText('Sin proyectos')).not.toBeInTheDocument()
  })

  it('lists real projects for the selected company', async () => {
    stubFetch({
      '/master-data/companies': [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL', country: null, fiscalId: null }],
      '/projects?company_id=c1': [
        { id: 'p1', companyId: 'c1', name: 'Torre Nexora II', code: 'PRJ-001', customerRef: null, manager: null, currencyCode: 'HNL', costCenterId: null, plannedStart: null, plannedEnd: null, actualEnd: null, status: 'PLANNING', description: null },
      ],
    })

    render(renderApp('/proyectos'))

    expect(await screen.findByText('Torre Nexora II')).toBeInTheDocument()
    expect(screen.getByText('Planificación')).toBeInTheDocument()
  })
})
