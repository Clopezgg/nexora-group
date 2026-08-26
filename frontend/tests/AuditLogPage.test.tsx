import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(companies: unknown[], auditRows: unknown[]) {
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
      if (url.includes('/audit?')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => auditRows } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('AuditLogPage', () => {
  it('shows an honest empty state when there are no companies yet', async () => {
    stubFetch([], [])

    render(renderApp('/control/auditoria'))

    expect(await screen.findByText(/configura una compañía primero/i)).toBeInTheDocument()
  })

  it('loads and displays real audit log entries from the API', async () => {
    stubFetch(
      [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }],
      [
        {
          id: 'a1',
          actorUserId: 'u1',
          action: 'ap.supplier_invoice.approve',
          entityType: 'ap.supplier_invoice',
          entityId: 'inv1',
          companyId: 'c1',
          projectId: null,
          before: { status: 'DRAFT' },
          after: { status: 'APPROVED' },
          correlationId: 'corr-1',
          createdAt: '2026-08-25T10:00:00Z',
        },
      ],
    )

    render(renderApp('/control/auditoria'))

    expect(await screen.findByText(/ap\.supplier_invoice\.approve/i)).toBeInTheDocument()
  })
})
