import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubAuthenticatedFetch(roles: string[], dashboard?: Record<string, unknown>) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ id: 'u1', email: 'user@nexora.group', fullName: 'Usuaria Demo', roles }),
        } as Response)
      }
      if (url.includes('/dashboard/summary') && dashboard) {
        return Promise.resolve({ ok: true, status: 200, json: async () => dashboard } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('HomePage', () => {
  it('shows the finance home with real treasury cards for Administrator', async () => {
    stubAuthenticatedFetch(['Administrator'], {
      treasuryBalance: 12000,
      periodIncome: 5000,
      periodExpense: 2000,
      activeProjects: 3,
      currency: 'HNL',
    })

    render(renderApp('/inicio'))

    expect(await screen.findByRole('heading', { name: /inicio — finanzas/i })).toBeInTheDocument()
    expect(await screen.findByText('Saldo Tesorería')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('shows the project home with real module shortcuts for Project Manager', async () => {
    stubAuthenticatedFetch(['Project Manager'])

    render(renderApp('/inicio'))

    expect(await screen.findByRole('heading', { name: /inicio — proyectos/i })).toBeInTheDocument()
    expect(screen.queryByText('Saldo Tesorería')).not.toBeInTheDocument()
    expect(screen.getByText('Presupuesto vs. actual')).toBeInTheDocument()
  })
})
