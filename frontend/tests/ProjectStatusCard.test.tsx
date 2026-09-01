import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'
import { ProjectStatusCard } from '../src/features/projects/ProjectStatusCard'
import type { Project } from '../src/types/project'

const PROJECT: Project = {
  id: 'p1', companyId: 'c1', name: 'Casa Residencial', code: 'CASA-1',
  customerId: null, customerRef: null, manager: null, managerUserId: null,
  currencyCode: 'HNL', costCenterId: null, plannedStart: null, plannedEnd: null,
  actualEnd: null, status: 'COMPLETED', description: null,
  addressLine1: null, addressLine2: null, city: null, stateDepartment: null,
  country: null, locationReference: null,
}

function wrap(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
}

describe('ProjectStatusCard (§6/§28 — sin botón obsoleto tras transición)', () => {
  it('tras COMPLETED → CLOSED, desaparece "Cerrar" y el estado pasa a Cerrado', async () => {
    let status = 'COMPLETED'
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input)
        const method = init?.method ?? 'GET'
        const ok = (body: unknown) => Promise.resolve({ ok: true, status: 200, json: async () => body } as Response)
        if (url.includes('/projects/p1/lifecycle')) {
          return ok(
            status === 'COMPLETED'
              ? {
                  currentStatus: 'COMPLETED', currentStatusLabel: 'Completado',
                  allowedTransitions: [
                    { status: 'CLOSED', label: 'Cerrado', sensitive: false },
                    { status: 'ACTIVE', label: 'Activo', sensitive: true },
                  ],
                  completedAt: '2026-09-01', closedAt: null, reopenedAt: null, archivedAt: null,
                }
              : {
                  currentStatus: 'CLOSED', currentStatusLabel: 'Cerrado',
                  allowedTransitions: [{ status: 'ARCHIVED', label: 'Archivado', sensitive: true }],
                  completedAt: '2026-09-01', closedAt: '2026-09-01', reopenedAt: null, archivedAt: null,
                },
          )
        }
        if (url.includes('/projects/p1/status') && method === 'POST') {
          status = 'CLOSED'
          return ok({ ...PROJECT, status: 'CLOSED', closedAt: '2026-09-01', completedAt: '2026-09-01' })
        }
        return ok({})
      }),
    )

    render(wrap(<ProjectStatusCard project={PROJECT} />))

    const closeBtn = await screen.findByRole('button', { name: /Cerrar administrativamente/i })
    await userEvent.click(closeBtn)

    await waitFor(() =>
      expect(screen.queryByRole('button', { name: /Cerrar administrativamente/i })).not.toBeInTheDocument(),
    )
    expect((await screen.findAllByText('Cerrado')).length).toBeGreaterThan(0)
  })
})
