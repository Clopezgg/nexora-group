import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(routes: Record<string, unknown | (() => { status: number; body: unknown })>) {
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
      for (const [fragment, value] of Object.entries(routes)) {
        if (url.includes(fragment)) {
          if (typeof value === 'function') {
            const { status, body } = (value as () => { status: number; body: unknown })()
            return Promise.resolve({ ok: status < 300, status, json: async () => body } as Response)
          }
          return Promise.resolve({ ok: true, status: 200, json: async () => value } as Response)
        }
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('BudgetPage', () => {
  it('shows null forecast metrics honestly when there is no progress data yet (no fake zeros)', async () => {
    stubFetch({
      '/budgets/summary': { authorized: '200000.00', committed: '0', accrued: '0', paid: '0', available: '200000.00' },
      '/budgets/active': () => ({ status: 200, body: { id: 'b1', projectId: 'p1', version: 'BASELINE', status: 'ACTIVE', currencyCode: 'HNL', previousBudgetId: null, changeOrderId: null, lines: [] } }),
      '/forecast': { bac: '200000.00', pv: null, ev: null, ac: '0', cpi: null, spi: null, etc: null, eac: null, vac: null },
    })

    render(renderApp('/proyectos/presupuestos'))

    expect(await screen.findByText('Forecast incompleto')).toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })

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

    render(renderApp('/proyectos/presupuestos'))

    expect(await screen.findByText('Selecciona un proyecto activo')).toBeInTheDocument()
  })
})
