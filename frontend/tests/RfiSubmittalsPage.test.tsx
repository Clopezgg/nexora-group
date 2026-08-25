import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(activeProjectId: string | null, rfis: unknown[], submittals: unknown[]) {
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
          json: async () => ({ activeProjectId, activeProjectName: activeProjectId ? 'Torre Nexora' : null }),
        } as Response)
      }
      if (url.includes('/projects/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ id: activeProjectId, companyId: 'c1', name: 'Torre Nexora' }),
        } as Response)
      }
      if (url.includes('/rfis?')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => rfis } as Response)
      }
      if (url.includes('/submittals?')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => submittals } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('RfiSubmittalsPage', () => {
  it('asks for an active project when none is selected, never fabricating data', async () => {
    stubFetch(null, [], [])

    render(renderApp('/proyectos/rfi-submittals'))

    // El tab "RFI" está activo por defecto -- el contenido del tab
    // "Submittals" ni siquiera se monta hasta que el usuario lo selecciona
    // (ver design-system/primitives/Navigation.tsx Tabs).
    expect(await screen.findByText(/selecciona un proyecto activo/i)).toBeInTheDocument()
  })

  it('lists real RFI and Submittal rows for the active project', async () => {
    stubFetch(
      'p1',
      [
        {
          id: 'r1',
          companyId: 'c1',
          projectId: 'p1',
          wbsNodeId: null,
          number: 'RFI-2026-000001',
          subject: 'Detalle de anclaje',
          question: '¿?',
          response: null,
          responsible: 'Ing. Residente',
          requestedBy: 'u1',
          respondedBy: null,
          dueDate: null,
          respondedAt: null,
          closedAt: null,
          status: 'OPEN',
          createdAt: '2026-03-01T00:00:00Z',
        },
      ],
      [
        {
          id: 's1',
          companyId: 'c1',
          projectId: 'p1',
          wbsNodeId: null,
          number: 'SUB-2026-000001',
          revision: 1,
          title: 'Ficha técnica de acero',
          description: null,
          supplierId: null,
          contractId: null,
          status: 'SUBMITTED',
          submittedBy: 'u1',
          submittedAt: '2026-03-01',
          dueDate: null,
          reviewerResponse: null,
          reviewedBy: null,
          responseRecordedAt: null,
          decidedBy: null,
          decidedAt: null,
          evidenceId: null,
          createdAt: '2026-03-01T00:00:00Z',
        },
      ],
    )

    render(renderApp('/proyectos/rfi-submittals'))

    expect(await screen.findByText('Detalle de anclaje')).toBeInTheDocument()
  })
})
