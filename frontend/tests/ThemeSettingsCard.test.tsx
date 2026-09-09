import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch({ themeId = null, density = null, companyThemeId = null }: {
  themeId?: string | null
  density?: string | null
  companyThemeId?: string | null
} = {}) {
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
        return Promise.resolve({ ok: true, status: 200, json: async () => ({ themeId, density }) } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            { id: 'c1', name: 'Constructora Nexora', code: 'NX', functionalCurrencyCode: 'HNL', defaultThemeId: companyThemeId, defaultDensity: null },
          ],
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
  return puts
}

describe('ThemeSettingsCard', () => {
  it('muestra las cinco familias en el orden canónico y las cuatro variantes SAP GUI', async () => {
    stubFetch()
    const user = userEvent.setup()
    render(renderApp('/control/configuracion'))

    const family = (await screen.findByLabelText('Familia')) as HTMLSelectElement
    expect([...family.options].map((option) => option.text)).toEqual([
      'NEXORA', 'Horizon', 'Quartz', 'Belize', 'SAP GUI',
    ])

    await user.selectOptions(family, 'sap-gui')
    await user.click(await screen.findByRole('button', { name: 'Cambiar a SAP GUI' }))
    expect([...((await screen.findByLabelText('Variante')) as HTMLSelectElement).options].map((option) => option.text)).toEqual([
      'SAP GUI Signature', 'SAP GUI Tradeshow', 'SAP GUI Horizon', 'SAP GUI Horizon Dark',
    ])
  })

  it('confirma antes de entrar y cancelar conserva exactamente el tema anterior', async () => {
    const puts = stubFetch()
    const user = userEvent.setup()
    render(renderApp('/control/configuracion'))
    await screen.findByText('Apariencia (Theme Engine)')
    expect(document.documentElement.dataset.nxTheme).toBe('nexora-horizon-light')

    await user.selectOptions(screen.getByLabelText('Familia'), 'sap-gui')
    expect(await screen.findByRole('dialog', { name: 'Cambiar a SAP GUI' })).toBeInTheDocument()
    expect(document.documentElement.dataset.nxTheme).toBe('nexora-horizon-light')
    expect((screen.getByLabelText('Familia') as HTMLSelectElement).value).toBe('nexora')

    await user.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(screen.queryByRole('dialog', { name: 'Cambiar a SAP GUI' })).not.toBeInTheDocument()
    expect(document.documentElement.dataset.nxTheme).toBe('nexora-horizon-light')
    expect(puts).toHaveLength(0)
  })

  it('el diálogo SAP usa nombres accesibles, cierra con Escape y restaura el foco', async () => {
    stubFetch()
    const user = userEvent.setup()
    render(renderApp('/control/configuracion'))
    const family = await screen.findByLabelText('Familia')

    await user.selectOptions(family, 'sap-gui')
    const dialog = await screen.findByRole('dialog', { name: 'Cambiar a SAP GUI' })
    expect(dialog).toHaveAttribute('aria-labelledby')
    expect(dialog).toHaveAttribute('aria-describedby')
    await user.keyboard('{Escape}')

    expect(screen.queryByRole('dialog', { name: 'Cambiar a SAP GUI' })).not.toBeInTheDocument()
    expect(family).toHaveFocus()
  })

  it('aceptar activa Signature globalmente; cambiar variante o salir no vuelve a preguntar', async () => {
    stubFetch()
    const user = userEvent.setup()
    render(renderApp('/control/configuracion'))
    await screen.findByText('Apariencia (Theme Engine)')

    await user.selectOptions(screen.getByLabelText('Familia'), 'sap-gui')
    await user.click(await screen.findByRole('button', { name: 'Cambiar a SAP GUI' }))
    await waitFor(() => {
      expect(document.documentElement.dataset.nxTheme).toBe('sap-gui-signature')
      expect(document.documentElement.dataset.nxFamily).toBe('sap-gui')
      expect(document.documentElement.dataset.nxAnatomy).toBe('sap-gui-signature')
      expect(document.documentElement.dataset.nxDensity).toBe('compact')
    })

    await user.selectOptions(screen.getByLabelText('Variante'), 'sap-gui-tradeshow')
    expect(screen.queryByRole('dialog', { name: 'Cambiar a SAP GUI' })).not.toBeInTheDocument()
    expect(document.documentElement.dataset.nxSapVariant).toBe('tradeshow')

    await user.selectOptions(screen.getByLabelText('Familia'), 'quartz')
    expect(screen.queryByRole('dialog', { name: 'Cambiar a SAP GUI' })).not.toBeInTheDocument()
    expect(document.documentElement.dataset.nxFamily).toBe('quartz')
  })

  it('carga una preferencia SAP guardada sin confirmación y puede cancelar una vista previa posterior', async () => {
    stubFetch({ themeId: 'sap-gui-tradeshow', density: 'compact' })
    const user = userEvent.setup()
    render(renderApp('/control/configuracion'))

    await waitFor(() => expect(document.documentElement.dataset.nxTheme).toBe('sap-gui-tradeshow'))
    expect(screen.queryByRole('dialog', { name: 'Cambiar a SAP GUI' })).not.toBeInTheDocument()
    await user.selectOptions(await screen.findByLabelText('Familia'), 'horizon')
    expect(document.documentElement.dataset.nxFamily).toBe('horizon')
    await user.click(screen.getByRole('button', { name: 'Cancelar vista previa' }))
    await waitFor(() => expect(document.documentElement.dataset.nxTheme).toBe('sap-gui-tradeshow'))
  })

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

  it.each(['sap-gui-signature', 'sap-gui-tradeshow'])('persiste la variante SAP %s', async (themeId) => {
    const puts = stubFetch()
    const user = userEvent.setup()
    render(renderApp('/control/configuracion'))

    await user.selectOptions(await screen.findByLabelText('Familia'), 'sap-gui')
    await user.click(await screen.findByRole('button', { name: 'Cambiar a SAP GUI' }))
    if (themeId === 'sap-gui-tradeshow') await user.selectOptions(screen.getByLabelText('Variante'), themeId)
    await user.click(screen.getByRole('button', { name: 'Guardar como mi preferencia' }))

    await waitFor(() => expect(puts.length).toBeGreaterThan(0))
    expect(JSON.parse(puts[0])).toMatchObject({ themeId })
  })
})
