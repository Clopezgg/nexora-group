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
            fullName: 'Admin Nexora',
            roles: ['Administrator'],
            permissions: [
              'treasury.account:read',
              'accounting.journal_entry:read',
              'project:read',
              'workflow.approval:read',
            ],
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
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }),
  )
}

describe('Mobile bottom navigation', () => {
  it('renders Inicio + RBAC-filtered middle slots + Más, and Más opens the drawer', async () => {
    stubFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))

    const nav = await screen.findByRole('navigation', { name: /navegación principal \(móvil\)/i })
    expect(within(nav).getByRole('link', { name: /inicio/i })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: /finanzas/i })).toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: /proyectos/i })).toBeInTheDocument()

    await user.click(within(nav).getByRole('button', { name: /más/i }))
    expect(await screen.findByRole('dialog', { name: /navegación/i })).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/buscar módulo/i)).toBeInTheDocument()
  })
})
