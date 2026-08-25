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
      if (url.includes('/context')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ activeProjectId: 'p1', activeProjectName: 'Torre Nexora II' }),
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

describe('DailyReportsPage', () => {
  it('prompts to select an active project when none is set', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL) => {
        const url = String(input)
        if (url.includes('/auth/me')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => ({ id: 'u1', email: 'a@a.com', fullName: 'A', roles: ['Administrator'] }) } as Response)
        }
        if (url.includes('/context')) {
          return Promise.resolve({ ok: true, status: 200, json: async () => ({ activeProjectId: null, activeProjectName: null }) } as Response)
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
      }),
    )

    render(renderApp('/proyectos/diario-de-obra'))

    expect(await screen.findByText('Selecciona un proyecto activo')).toBeInTheDocument()
  })

  it('lists real daily site reports for the active project, never fabricated rows', async () => {
    stubFetch({
      '/site-reports?projectId=p1': [
        {
          id: 'r1',
          projectId: 'p1',
          reportDate: '2026-03-01',
          weather: 'SUNNY',
          workforceSummary: '12 albañiles',
          activitiesPerformed: 'Vaciado de losa nivel 2',
          equipmentUsed: null,
          materialsUsed: null,
          incidents: null,
          observations: null,
          authorId: 'u1',
          status: 'DRAFT',
          approvedById: null,
          approvedAt: null,
          photos: [],
        },
      ],
    })

    render(renderApp('/proyectos/diario-de-obra'))

    expect(await screen.findByText('Vaciado de losa nivel 2')).toBeInTheDocument()
    expect(screen.getByText('Borrador')).toBeInTheDocument()
  })

  it('shows an honest empty state when there are no reports yet', async () => {
    stubFetch({ '/site-reports?projectId=p1': [] })

    render(renderApp('/proyectos/diario-de-obra'))

    expect(await screen.findByText('Sin reportes diarios')).toBeInTheDocument()
  })
})
