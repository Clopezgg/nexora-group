import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

const COMPANY = {
  id: 'c1',
  name: 'Constructora Nexora',
  code: null,
  legalName: null,
  functionalCurrencyCode: 'HNL',
}

const SEARCH_RESULT = {
  id: 'proj-99',
  label: 'Torre Reforma Norte',
  group: 'Proyectos',
  path: '/proyectos',
  entityType: 'project',
}

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
            fullName: 'Administradora',
            roles: ['Administrator'],
          }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [COMPANY] } as Response)
      }
      if (url.includes('/search?')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => [SEARCH_RESULT] } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('Global search in the command palette', () => {
  it('shows a real /api/search result and navigates to it on click', async () => {
    stubFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))

    await screen.findByRole('heading', { name: /inicio/i })
    await user.click(screen.getByRole('button', { name: /búsqueda global/i }))

    const input = await screen.findByPlaceholderText(/ir a…/i)
    await user.type(input, 'Reforma')

    const resultButton = await screen.findByRole('option', { name: /torre reforma norte/i })
    await user.click(resultButton)

    expect(await screen.findByRole('heading', { name: /^proyectos$/i })).toBeInTheDocument()
  })

  it('keeps showing local nav matches while the remote search is still loading', async () => {
    stubFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))

    await screen.findByRole('heading', { name: /inicio/i })
    await user.click(screen.getByRole('button', { name: /búsqueda global/i }))

    const input = await screen.findByPlaceholderText(/ir a…/i)
    // "Proyectos" matches a real nav item locally -- this must render
    // immediately, before the debounced /api/search call resolves.
    await user.type(input, 'Proyec')

    const listbox = await screen.findByRole('listbox')
    const options = await within(listbox).findAllByRole('option')
    expect(options).toHaveLength(1)
    expect(options[0]).toHaveTextContent('Proyectos')
  })
})
