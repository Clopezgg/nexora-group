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
  it('applies the selected family + variant to the document root on preview', async () => {
    stubFetch()
    const user = userEvent.setup()
    render(renderApp('/control/configuracion'))

    expect(await screen.findByText('Apariencia (Theme Engine)')).toBeInTheDocument()

    await user.selectOptions(await screen.findByLabelText('Familia'), 'quartz')
    await user.selectOptions(await screen.findByLabelText('Variante'), 'quartz-dark')

    await waitFor(() => {
      expect(document.documentElement.dataset.nxTheme).toBe('quartz-dark')
      expect(document.documentElement.dataset.nxFamily).toBe('quartz')
    })
  })

  it('exposes the Finance Dense density and the UI scale control', async () => {
    stubFetch()
    const user = userEvent.setup()
    render(renderApp('/control/configuracion'))

    const density = (await screen.findByLabelText('Densidad')) as HTMLSelectElement
    expect([...density.options].map((o) => o.value)).toContain('finance-dense')
    await user.selectOptions(density, 'finance-dense')
    await waitFor(() => expect(document.documentElement.dataset.nxDensity).toBe('finance-dense'))

    const scale = (await screen.findByLabelText('Escala de la interfaz')) as HTMLSelectElement
    expect([...scale.options].map((o) => o.value)).toEqual(['90', '100', '110'])
  })

  it('persists the user preference through PUT /me/preferences', async () => {
    const puts = stubFetch()
    const user = userEvent.setup()
    render(renderApp('/control/configuracion'))

    await user.selectOptions(await screen.findByLabelText('Familia'), 'quartz')
    await user.selectOptions(await screen.findByLabelText('Variante'), 'quartz-light')
    await user.click(screen.getByRole('button', { name: 'Guardar como mi preferencia' }))

    await waitFor(() => expect(puts.length).toBeGreaterThan(0))
    expect(JSON.parse(puts[0])).toMatchObject({ themeId: 'quartz-light' })
  })
})
