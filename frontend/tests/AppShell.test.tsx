import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubAuthenticatedFetch() {
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
            fullName: 'Administradora',
            roles: ['Administrator'],
          }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('AppLayout shell', () => {
  it('opens the mobile nav drawer from the topbar toggle', async () => {
    stubAuthenticatedFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))

    await screen.findByRole('heading', { name: /inicio/i })
    await user.click(screen.getByRole('button', { name: /abrir navegación/i }))

    expect(await screen.findByRole('dialog', { name: /navegación/i })).toBeInTheDocument()
  })

  it('opens the command palette from the topbar search button (not just the keyboard shortcut)', async () => {
    stubAuthenticatedFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))

    await screen.findByRole('heading', { name: /inicio/i })
    expect(screen.queryByPlaceholderText(/ir a…/i)).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /búsqueda global/i }))

    expect(await screen.findByPlaceholderText(/ir a…/i)).toBeInTheDocument()
  })
})
