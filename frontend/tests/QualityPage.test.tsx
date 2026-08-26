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

describe('QualityPage', () => {
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

    render(renderApp('/proyectos/calidad'))

    expect(await screen.findByText('Selecciona un proyecto activo')).toBeInTheDocument()
  })

  it('lists real quality inspections on the default tab, never fabricated rows', async () => {
    stubFetch({
      '/quality/inspections?projectId=p1': [
        {
          id: 'i1',
          projectId: 'p1',
          wbsNodeId: null,
          inspectionType: 'REBAR_PLACEMENT',
          inspectionDate: '2026-03-01',
          inspectorId: 'u1',
          result: 'PASS',
          notes: null,
          evidenceId: null,
        },
      ],
      '/quality/non-conformances?projectId=p1': [],
    })

    render(renderApp('/proyectos/calidad'))

    expect(await screen.findByText('REBAR_PLACEMENT')).toBeInTheDocument()
    expect(screen.getByText('PASS')).toBeInTheDocument()
  })

  it('switches to the non-conformances tab and lists real data', async () => {
    stubFetch({
      '/quality/inspections?projectId=p1': [],
      '/quality/non-conformances?projectId=p1': [
        {
          id: 'nc1',
          projectId: 'p1',
          qualityInspectionId: null,
          description: 'Recubrimiento de acero insuficiente',
          responsibleUserId: 'u1',
          dueDate: '2026-03-10',
          status: 'OPEN',
          closedAt: null,
          evidenceId: null,
        },
      ],
    })

    render(renderApp('/proyectos/calidad'))

    const tab = await screen.findByRole('tab', { name: 'No conformidades' })
    fireEvent.click(tab)

    expect(await screen.findByText('Recubrimiento de acero insuficiente')).toBeInTheDocument()
  })
})
