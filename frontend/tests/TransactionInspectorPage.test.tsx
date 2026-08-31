import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch() {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            id: 'u1',
            email: 'admin@nexora.group',
            fullName: 'Admin',
            roles: ['Administrator'],
            permissions: ['accounting.journal_entry:read'],
          }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [{ id: 'c1', name: 'Constructora Nexora', functionalCurrencyCode: 'HNL' }],
        } as Response)
      }
      if (url.includes('/accounting/journal-entries') && url.includes('/inspect')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            documentId: 'd1',
            documentNumber: 'REM-2026-0001',
            documentTypeCode: 'REM',
            scope: 'CENTRAL',
            status: 'POSTED',
            currencyCode: 'HNL',
            description: 'Remesa recibida',
            projectName: null,
            postedAt: '2026-01-01T00:00:00Z',
            totalDebit: 10000,
            totalCredit: 10000,
            balanced: true,
            sourceEvent: { kind: 'REMITTANCE', label: 'Remesa recibida', reference: 'Aportante Principal', entityId: 'r1' },
            lines: [
              { accountCode: '1100', accountName: 'Bancos', debit: 10000, credit: 0, description: null, projectName: null, costCenterName: null },
              { accountCode: '3100', accountName: 'Aportes', debit: 0, credit: 10000, description: null, projectName: null, costCenterName: null },
            ],
            reversesDocumentId: null,
            reversalReason: null,
            reversedByDocumentIds: [],
            evidence: [],
          }),
        } as Response)
      }
      if (url.includes('/accounting/journal-entries')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            { id: 'd1', documentNumber: 'REM-2026-0001', companyId: 'c1', scope: 'CENTRAL', projectId: null, currencyCode: 'HNL', status: 'POSTED', description: 'Remesa recibida' },
          ],
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('TransactionInspectorPage', () => {
  it('does inverse drill-down from the GL entry to its business event', async () => {
    stubFetch()
    const user = userEvent.setup()
    render(renderApp('/finanzas/inspector'))

    await user.selectOptions(await screen.findByLabelText('Asiento a inspeccionar'), 'd1')

    expect(await screen.findByText('Remesa recibida · Aportante Principal')).toBeInTheDocument()
    expect(screen.getByText('Doble partida OK')).toBeInTheDocument()
    expect(screen.getByText('1100 — Bancos')).toBeInTheDocument()
    expect(screen.getByText('3100 — Aportes')).toBeInTheDocument()
  })
})
