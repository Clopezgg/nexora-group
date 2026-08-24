import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

describe('DashboardPage', () => {
  it('renders zeroed cards for a fresh database without hardcoding fake amounts', async () => {
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
              fullName: 'Administrador',
              roles: ['Administrator'],
            }),
          } as Response)
        }
        if (url.includes('/dashboard/summary')) {
          return Promise.resolve({
            ok: true,
            status: 200,
            json: async () => ({
              treasuryBalance: 0,
              periodIncome: 0,
              periodExpense: 0,
              activeProjects: 0,
              currency: 'MXN',
            }),
          } as Response)
        }
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
      }),
    )

    render(renderApp('/dashboard'))

    expect(await screen.findByText('Saldo Tesorería')).toBeInTheDocument()
    const zeroValues = await screen.findAllByText('$0')
    expect(zeroValues.length).toBeGreaterThan(0)
  })
})
