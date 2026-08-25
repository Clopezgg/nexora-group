import { fireEvent, render, screen } from '@testing-library/react'
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

describe('SafetyPage', () => {
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

    render(renderApp('/proyectos/seguridad'))

    expect(await screen.findByText('Selecciona un proyecto activo')).toBeInTheDocument()
  })

  it('lists real safety observations on the default tab, never fabricated rows', async () => {
    stubFetch({
      '/safety/observations?projectId=p1': [
        {
          id: 'o1',
          projectId: 'p1',
          observationDate: '2026-03-01',
          category: 'PPE',
          description: 'Trabajador sin casco',
          severity: 'MEDIUM',
          responsibleUserId: 'u1',
          correctiveAction: null,
          status: 'OPEN',
          closedAt: null,
          evidenceId: null,
        },
      ],
      '/safety/incidents?projectId=p1': [],
    })

    render(renderApp('/proyectos/seguridad'))

    expect(await screen.findByText('Trabajador sin casco')).toBeInTheDocument()
    expect(screen.getByText('MEDIUM')).toBeInTheDocument()
  })

  it('switches to the incidents tab and lists real data', async () => {
    stubFetch({
      '/safety/observations?projectId=p1': [],
      '/safety/incidents?projectId=p1': [
        {
          id: 'inc1',
          projectId: 'p1',
          incidentDate: '2026-03-01',
          description: 'Caída de altura en andamio',
          severity: 'HIGH',
          responsibleUserId: 'u1',
          correctiveAction: null,
          status: 'OPEN',
          closedAt: null,
          evidenceId: null,
        },
      ],
    })

    render(renderApp('/proyectos/seguridad'))

    const tab = await screen.findByRole('tab', { name: 'Incidentes' })
    fireEvent.click(tab)

    expect(await screen.findByText('Caída de altura en andamio')).toBeInTheDocument()
  })
})
