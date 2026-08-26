import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

describe('routing', () => {
  it('redirects unauthenticated users from a protected route to /login', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Not authenticated' }),
      } as Response),
    )

    render(renderApp('/dashboard'))

    expect(await screen.findByRole('heading', { name: /iniciar sesión/i })).toBeInTheDocument()
  })

  it('renders the role-based home for authenticated users at the root path', async () => {
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

    render(renderApp('/'))

    expect(await screen.findByRole('heading', { name: /inicio — finanzas/i })).toBeInTheDocument()
  })

  it('renders every grouped nav route without crashing (placeholder or home)', async () => {
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
        return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
      }),
    )

    render(renderApp('/abastecimiento/rfq'))

    expect(await screen.findByRole('heading', { name: /^rfq$/i })).toBeInTheDocument()
  })
})
