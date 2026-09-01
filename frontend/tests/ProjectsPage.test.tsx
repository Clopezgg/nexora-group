import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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
    const row = screen.getByText('Torre Nexora II').closest('tr') as HTMLElement
    expect(within(row).getByText('Planificación')).toBeInTheDocument()
  })

  it('creates a project through the guided wizard, sending the real location (§11/§17)', async () => {
    let createPayload: Record<string, unknown> | null = null
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const method = init?.method ?? 'GET'
        if (url.includes('/auth/me')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => ({ id: 'u1', email: 'a@nexora.group', fullName: 'Admin', roles: ['Administrator'] }) } as Response)
        }
        if (url.includes('/master-data/companies')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }] } as Response)
        }
        if (url.includes('/master-data/users')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => [{ id: 'mgr1', fullName: 'Ing. Responsable' }] } as Response)
        }
        if (url.endsWith('/projects') && method === 'POST') {
          createPayload = JSON.parse(String(init?.body))
          return Promise.resolve({ ok: true, status: 201, json: async () => ({ id: 'p9', companyId: 'c1', name: createPayload?.name, status: 'PLANNING' }) } as Response)
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
      }),
    )

    render(renderApp('/proyectos'))
    await userEvent.click(await screen.findByRole('button', { name: 'Nuevo proyecto' }))
    await userEvent.type(screen.getByLabelText('Nombre del proyecto'), 'Puente Río Grande')
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }))
    // Paso 2 — ubicación real.
    await userEvent.type(screen.getByLabelText('Ciudad'), 'Comayagua')
    await userEvent.type(screen.getByLabelText('Departamento / Estado'), 'Comayagua')
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }))
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' })) // alcance
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' })) // equipo
    await userEvent.click(screen.getByRole('button', { name: 'Crear como borrador' }))

    await waitFor(() =>
      expect(createPayload).toMatchObject({
        name: 'Puente Río Grande',
        city: 'Comayagua',
        stateDepartment: 'Comayagua',
      }),
    )
  })
})
