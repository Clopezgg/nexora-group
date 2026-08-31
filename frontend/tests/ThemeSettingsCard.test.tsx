import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch() {
  const puts: string[] = []
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ id: 'u1', email: 'admin@nexora.group', fullName: 'Admin', roles: ['Administrator'] }),
        } as Response)
      }
      if (url.includes('/me/preferences')) {
        if (init?.method === 'PUT') puts.push(String(init.body))
        return Promise.resolve({ ok: true, status: 200, json: async () => ({ themeId: null, density: null }) } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            { id: 'c1', name: 'Constructora Nexora', code: 'NX', functionalCurrencyCode: 'HNL', defaultThemeId: null, defaultDensity: null },
          ],
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
  return puts
}

describe('ThemeSettingsCard', () => {
  it('renders the preset gallery and applies a theme to the document root on preview', async () => {
    stubFetch()
    const user = userEvent.setup()
    render(renderApp('/control/configuracion'))

    expect(await screen.findByText('Apariencia (Theme Engine)')).toBeInTheDocument()
    const darkSwatch = await screen.findByRole('button', { name: /NEXORA Dark/ })
    await user.click(darkSwatch)

    await waitFor(() => {
      expect(document.documentElement.dataset.nxTheme).toBe('nexora-dark')
    })
  })

  it('persists the user preference through PUT /me/preferences', async () => {
    const puts = stubFetch()
    const user = userEvent.setup()
    render(renderApp('/control/configuracion'))

    await user.click(await screen.findByRole('button', { name: /Quartz \(claro\)/ }))
    await user.click(screen.getByRole('button', { name: 'Guardar como mi preferencia' }))

    await waitFor(() => expect(puts.length).toBeGreaterThan(0))
    expect(JSON.parse(puts[0])).toMatchObject({ themeId: 'quartz-light' })
  })
})
