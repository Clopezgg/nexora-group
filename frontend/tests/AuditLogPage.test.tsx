import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
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

  it('shows humanized events in the table and technical fields only in the detail drawer', async () => {
    stubFetch(
      [{ id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' }],
      [
        {
          id: 'a1',
          actorUserId: 'u1',
          actorFullName: 'Carlos Humberto López',
          actorEmail: 'carlos@nexora.group',
          action: 'ap.supplier_invoice.approve',
          entityType: 'ap.supplier_invoice',
          entityId: 'inv-uuid-1',
          companyId: 'c1',
          projectId: null,
          before: { status: 'DRAFT', secret: 'should-not-render' },
          after: { status: 'APPROVED' },
          correlationId: 'corr-1',
          createdAt: '2026-08-25T10:00:00Z',
        },
      ],
    )

    render(renderApp('/control/auditoria'))

    // Primary view: human language, no raw code, actor name not UUID.
    expect(await screen.findByText('Factura de proveedor · Aprobación')).toBeInTheDocument()
    expect(screen.getByText('Cuentas por pagar')).toBeInTheDocument()
    expect(screen.getByText('Carlos Humberto López')).toBeInTheDocument()
    expect(screen.queryByText('ap.supplier_invoice.approve')).not.toBeInTheDocument()
    expect(screen.queryByText('inv-uuid-1')).not.toBeInTheDocument()

    // Detail drawer: technical fields available on demand, secrets redacted.
    await userEvent.click(screen.getByRole('button', { name: /ver detalles/i }))
    expect(await screen.findByText('ap.supplier_invoice.approve')).toBeInTheDocument()
    expect(screen.getByText('inv-uuid-1')).toBeInTheDocument()
    expect(screen.getByText('corr-1')).toBeInTheDocument()
    expect(screen.getByText(/"status": "APPROVED"/)).toBeInTheDocument()
    expect(screen.getByText(/\[oculto\]/)).toBeInTheDocument()
    expect(screen.queryByText(/should-not-render/)).not.toBeInTheDocument()
  })
})
