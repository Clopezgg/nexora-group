import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

const COMPANY = { id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }
const WORKER = {
  id: 'w1',
  companyId: 'c1',
  fullName: 'Juan Pérez',
  roleTitle: 'Albañil',
  standardHourlyRate: '125.50',
  active: true,
}
const CREW = { id: 'crew1', companyId: 'c1', projectId: null, name: 'Cuadrilla Estructuras', status: 'ACTIVE' }

function stubFetch(overrides: {
  companies?: unknown[]
  crews?: unknown[]
  workers?: unknown[]
  crewDetail?: unknown
  onCreateCrew?: () => void
  onAddMember?: () => void
  onRemoveMember?: () => void
}) {
  const companies = overrides.companies ?? [COMPANY]
  const workers = overrides.workers ?? [WORKER]
  let crews = overrides.crews ?? [CREW]
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
        return Promise.resolve({ ok: true, status: 200, json: async () => companies } as Response)
      }
      if (url.includes('/context')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ activeProjectId: null, activeProjectName: null }),
        } as Response)
      }
      if (url.includes('/workforce/workers')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => workers } as Response)
      }
      if (method === 'POST' && url.endsWith('/workforce/crews')) {
        overrides.onCreateCrew?.()
        crews = [...crews, CREW]
        return Promise.resolve({ ok: true, status: 201, json: async () => CREW } as Response)
      }
      if (method === 'POST' && url.includes('/members') && !url.includes('members/')) {
        overrides.onAddMember?.()
        return Promise.resolve({ ok: true, status: 201, json: async () => ({ id: 'cm1', crewId: 'crew1', workerId: 'w1' }) } as Response)
      }
      if (method === 'DELETE' && url.includes('/members/')) {
        overrides.onRemoveMember?.()
        return Promise.resolve({ ok: true, status: 204, json: async () => undefined } as Response)
      }
      if (url.match(/\/workforce\/crews\/[^/?]+$/)) {
        return Promise.resolve({ ok: true, status: 200, json: async () => overrides.crewDetail ?? { ...CREW, members: [] } } as Response)
      }
      if (url.includes('/workforce/crews')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => crews } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }),
  )
}

describe('CrewsPage', () => {
  it('shows an honest empty state when there are no companies yet', async () => {
    stubFetch({ companies: [] })

    render(renderApp('/recursos/cuadrillas'))

    expect(await screen.findByText(/configura una compañía primero/i)).toBeInTheDocument()
  })

  it('lists real crews from the API', async () => {
    stubFetch({})

    render(renderApp('/recursos/cuadrillas'))

    expect(await screen.findByText('Cuadrilla Estructuras')).toBeInTheDocument()
  })

  it('creates a new crew through the real API', async () => {
    const onCreateCrew = vi.fn()
    stubFetch({ crews: [], onCreateCrew })

    render(renderApp('/recursos/cuadrillas'))
    await userEvent.click(await screen.findByRole('button', { name: /nueva cuadrilla/i }))
    await userEvent.type(screen.getByLabelText(/nombre/i), 'Cuadrilla Nueva')
    await userEvent.click(screen.getByRole('button', { name: /guardar/i }))

    expect(onCreateCrew).toHaveBeenCalled()
  })

  it('manages crew membership through the real API', async () => {
    const onAddMember = vi.fn()
    const onRemoveMember = vi.fn()
    stubFetch({
      crewDetail: { ...CREW, members: [WORKER] },
      onAddMember,
      onRemoveMember,
    })

    render(renderApp('/recursos/cuadrillas'))
    await userEvent.click(await screen.findByRole('button', { name: /miembros/i }))

    const modal = await screen.findByRole('dialog')
    expect(await within(modal).findByText('Juan Pérez')).toBeInTheDocument()

    await userEvent.click(within(modal).getByRole('button', { name: /quitar/i }))
    expect(onRemoveMember).toHaveBeenCalled()
  })
})
