import { render, screen, within } from '@testing-library/react'
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
            permissions: ['reports.trial_balance:read', 'reports.general_ledger:read'],
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
      if (url.includes('/reports/trial-balance')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            rows: [
              { accountId: 'acc-6000', accountCode: '6000', accountName: 'Gastos', debitBalance: '100.00', creditBalance: '0' },
            ],
            totalDebit: '100.00',
            totalCredit: '100.00',
          }),
        } as Response)
      }
      if (url.includes('/reports/general-ledger')) {
        const filtered = url.includes('accountId=acc-6000')
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            rows: filtered
              ? [
                  {
                    lineId: 'l1',
                    documentId: 'doc-1',
                    documentNumber: 'JRN-2026-0001',
                    postedAt: '2026-08-01',
                    documentStatus: 'POSTED',
                    accountId: 'acc-6000',
                    accountCode: '6000',
                    accountName: 'Gastos',
                    accountType: 'EXPENSE',
                    scope: 'GENERAL',
                    projectId: null,
                    description: 'Gasto',
                    debitAmount: '100.00',
                    creditAmount: '0',
                  },
                ]
              : [],
            total: filtered ? 1 : 0,
            offset: 0,
            limit: 25,
            totalDebit: '100.00',
            totalCredit: '0',
          }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('Financial Reporting Center — drill-down', () => {
  it('drills from a trial-balance account to the general ledger filtered by that account, then to the inspector', async () => {
    stubFetch()
    const user = userEvent.setup()
    render(renderApp('/control/reportes'))

    // Balance de Comprobación cargado.
    expect(await screen.findByText('Gastos')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '6000' }))

    // Cambió a Libro Mayor filtrado por la cuenta.
    expect(await screen.findByText(/Filtrado por cuenta: 6000 — Gastos/)).toBeInTheDocument()
    const docLink = await screen.findByRole('link', { name: 'JRN-2026-0001' })
    expect(docLink).toHaveAttribute('href', '/finanzas/inspector?documentId=doc-1')
  })
})
