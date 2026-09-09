import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubAuthenticatedFetch(themeId: string | null = null) {
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
      if (url.includes('/me/preferences')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => ({ themeId, density: themeId ? 'compact' : null }) } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [{ id: 'c1', name: 'Constructora Nexora', code: 'NX', functionalCurrencyCode: 'HNL', defaultThemeId: null, defaultDensity: null }],
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('AppLayout shell', () => {
  it.each(['sap-gui-signature', 'sap-gui-tradeshow', 'sap-gui-horizon', 'sap-gui-horizon-dark'])('renderiza el shell global completo para %s', async (themeId) => {
    stubAuthenticatedFetch(themeId)
    render(renderApp('/inicio'))

    expect(await screen.findByText('NEXORA — Gestión empresarial')).toBeInTheDocument()
    expect(screen.getByRole('menubar', { name: 'Barra de menús SAP GUI' })).toBeInTheDocument()
    expect(screen.getByRole('banner', { name: 'Barra de herramientas SAP GUI' })).toBeInTheDocument()
    expect(screen.getByRole('tree', { name: 'Navegación principal', hidden: true })).toBeInTheDocument()
    expect(screen.getByRole('status', { name: 'Contexto SAP GUI' })).toBeInTheDocument()
    expect(document.documentElement.dataset.nxSapVariant).toBe(themeId.replace('sap-gui-', ''))
  })

  it('no monta chrome SAP GUI para las cuatro familias modernas', async () => {
    stubAuthenticatedFetch('quartz-light')
    render(renderApp('/inicio'))
    await screen.findByRole('heading', { name: /inicio/i })

    expect(screen.queryByRole('menubar', { name: 'Barra de menús SAP GUI' })).not.toBeInTheDocument()
    expect(screen.queryByRole('status', { name: 'Contexto SAP GUI' })).not.toBeInTheDocument()
    expect(screen.queryByText('NEXORA — Gestión empresarial')).not.toBeInTheDocument()
  })

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
