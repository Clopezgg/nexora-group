import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(allReconciled: boolean) {
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
            permissions: ['accounting.reconciliation:read'],
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
      if (url.includes('/accounting/reconciliation/subledger-gl')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            allReconciled,
            lines: [
              {
                subledger: 'TREASURY',
                subledgerTotal: 50000,
                glTotal: 50000,
                difference: 0,
                reconciled: true,
                detail: 'Tesorería vs GL',
              },
              {
                subledger: 'ACCOUNTS_PAYABLE',
                subledgerTotal: 1000,
                glTotal: allReconciled ? 1000 : 850,
                difference: allReconciled ? 0 : 150,
                reconciled: allReconciled,
                detail: 'AP vs control',
              },
            ],
          }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('SubledgerReconciliationPage', () => {
  it('shows every subledger reconciled against the GL control account', async () => {
    stubFetch(true)
    render(renderApp('/finanzas/conciliacion-subledger'))

    expect(await screen.findByRole('heading', { name: 'Conciliación Subledger ↔ GL' })).toBeInTheDocument()
    expect(await screen.findByText('Todos los subledgers cuadran contra el GL')).toBeInTheDocument()
    expect(screen.getAllByText('Cuadra').length).toBeGreaterThan(0)
  })

  it('flags a subledger that does not reconcile', async () => {
    stubFetch(false)
    render(renderApp('/finanzas/conciliacion-subledger'))

    expect(await screen.findByText('DESCUADRE')).toBeInTheDocument()
    expect(screen.getByText(/Hay descuadres/)).toBeInTheDocument()
  })
})
