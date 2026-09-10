import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

const PERMISSIONS = [
  'workflow.approval:read',
  'treasury.account:read',
  'project:read',
  'document.document:read',
  'audit.log:read',
]

function setViewport(width: number, height = 900) {
  const hd = (window as unknown as { happyDOM?: { setViewport: (viewport: { width: number; height: number }) => void } }).happyDOM
  hd?.setViewport({ width, height })
}

function stubSapFetch(themeId: string | null = 'sap-gui-signature') {
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
            permissions: PERMISSIONS,
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
      if (url.includes('/fiscal/periods/current')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            period: { startDate: '2026-01-01', endDate: '2026-01-31', periodNumber: 1, status: 'OPEN' },
            fiscalYear: { code: '2026' },
          }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => [] } as Response)
    }),
  )
}

/**
 * Los grupos del árbol y sus links pueden compartir etiqueta ('Inicio' es
 * grupo y ruta): se desambigua por data-kind en lugar de consultas de rol
 * con nombre ambiguo.
 */
function treeGroup(name: string): HTMLElement {
  const matches = screen.getAllByRole('treeitem', { name })
  const group = matches.find((element) => (element as HTMLElement).dataset.kind === 'group')
  if (!group) throw new Error(`grupo del árbol no encontrado: ${name}`)
  return group as HTMLElement
}

async function findTreeGroup(name: string): Promise<HTMLElement> {
  return waitFor(
    () => treeGroup(name),
    { timeout: 5000 },
  )
}

describe('SapWorkstation — árbol Easy Access', () => {
  it('abre inicialmente solo el grupo activo y refleja aria-expanded real', async () => {
    setViewport(1440)
    stubSapFetch()
    render(renderApp('/inicio'))
    await screen.findByText('NEXORA — Gestión empresarial', undefined, { timeout: 5000 })

    expect(await findTreeGroup('Inicio')).toHaveAttribute('aria-expanded', 'true')
    expect(treeGroup('Finanzas')).toHaveAttribute('aria-expanded', 'false')
    // Grupo colapsado: sus links no están en el árbol.
    expect(screen.queryByRole('treeitem', { name: 'Tesorería' })).not.toBeInTheDocument()
  })

  it('colapsar/expandir persiste y el rerender no reabre a la fuerza', async () => {
    setViewport(1440)
    stubSapFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))
    await screen.findByText('NEXORA — Gestión empresarial', undefined, { timeout: 5000 })
    await findTreeGroup('Inicio')

    await user.click(treeGroup('Inicio'))
    expect(treeGroup('Inicio')).toHaveAttribute('aria-expanded', 'false')

    await user.click(treeGroup('Finanzas'))
    expect(treeGroup('Finanzas')).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('treeitem', { name: 'Tesorería' })).toBeInTheDocument()

    // Un re-render del shell (aquí vía drawer: cambia estado del
    // SapWorkstation sin desmontar el árbol) no reabre grupos a la fuerza.
    const toolbarToggle = document.querySelector('.nx-sap-toolbar button[aria-label="Abrir navegación"]')
    if (!toolbarToggle) throw new Error('toggle de toolbar SAP no encontrado')
    await user.click(toolbarToggle as HTMLElement)
    const navDialog = await screen.findByRole('dialog', { name: 'Navegación' }, { timeout: 5000 })
    await user.click(within(navDialog).getByRole('button', { name: 'Cerrar' }))
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Navegación' })).not.toBeInTheDocument())
    expect(treeGroup('Inicio')).toHaveAttribute('aria-expanded', 'false')
    expect(treeGroup('Finanzas')).toHaveAttribute('aria-expanded', 'true')
  })

  it('teclado: ArrowRight expande, ArrowLeft colapsa, Up/Down/Home/End mueven foco, Enter alterna', async () => {
    setViewport(1440)
    stubSapFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))
    await screen.findByText('NEXORA — Gestión empresarial', undefined, { timeout: 5000 })
    await findTreeGroup('Finanzas')

    treeGroup('Finanzas').focus()
    await user.keyboard('{ArrowRight}')
    expect(treeGroup('Finanzas')).toHaveAttribute('aria-expanded', 'true')

    await user.keyboard('{ArrowLeft}')
    expect(treeGroup('Finanzas')).toHaveAttribute('aria-expanded', 'false')

    await user.keyboard('{Enter}')
    expect(treeGroup('Finanzas')).toHaveAttribute('aria-expanded', 'true')

    await user.keyboard('{End}')
    expect(document.activeElement?.getAttribute('role')).toBe('treeitem')
    await user.keyboard('{Home}')
    expect(document.activeElement?.textContent).toContain('Inicio')

    // Desde el grupo 'Inicio', ArrowDown baja al link 'Inicio' (misma
    // etiqueta, distinto nivel): verifica el nivel, no el texto.
    await user.keyboard('{ArrowDown}')
    expect(document.activeElement?.getAttribute('role')).toBe('treeitem')
    expect((document.activeElement as HTMLElement | null)?.dataset.kind).toBe('link')
  })

  it('oculta rutas sin permiso y el link activo marca aria-selected/aria-current', async () => {
    setViewport(1440)
    stubSapFetch()
    render(renderApp('/inicio'))
    await screen.findByText('NEXORA — Gestión empresarial', undefined, { timeout: 5000 })

    // Sin permiso de CRM: nada comercial visible.
    expect(screen.queryByRole('treeitem', { name: 'Leads' })).not.toBeInTheDocument()
    expect(screen.queryByRole('treeitem', { name: 'Clientes' })).not.toBeInTheDocument()

    const active = screen.getByRole('treeitem', { name: 'Inicio', selected: true })
    expect(active).toHaveAttribute('aria-current', 'page')
  })

  it('la variante drawer filtra por búsqueda y al limpiar restaura el estado', async () => {
    setViewport(800)
    stubSapFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))
    await screen.findByText('NEXORA — Gestión empresarial', undefined, { timeout: 5000 })

    // Abrir el drawer móvil desde el toggle de la Topbar (hay dos botones
    // 'Abrir navegación': Topbar + toolbar SAP; aquí importa el de la Topbar).
    const navToggle = document.querySelector('.nx-topbar__nav-toggle')
    if (!navToggle) throw new Error('toggle de navegación no visible en viewport móvil')
    await user.click(navToggle as HTMLElement)
    const dialog = await screen.findByRole('dialog', { name: 'Navegación' }, { timeout: 5000 })
    const search = within(dialog).getByLabelText('Buscar módulo')
    await user.type(search, 'tesorería')
    expect(await within(dialog).findByRole('treeitem', { name: 'Tesorería' }, { timeout: 5000 })).toBeInTheDocument()
    expect(within(dialog).queryByRole('treeitem', { name: 'Proyectos' })).not.toBeInTheDocument()

    await user.clear(search)
    // Estado coherente: grupo activo abierto, Finanzas colapsada de nuevo.
    const dialogGroups = within(dialog).getAllByRole('treeitem', { name: 'Inicio' })
    const dialogInicio = dialogGroups.find((element) => (element as HTMLElement).dataset.kind === 'group')
    expect(dialogInicio).toHaveAttribute('aria-expanded', 'true')
    expect(within(dialog).queryByRole('treeitem', { name: 'Tesorería' })).not.toBeInTheDocument()
  })
})

describe('SapWorkstation — menubar real', () => {
  // La menubar es visible en desktop y tablet/móvil (overflow-x).
    it('abre Sistema, navega con teclado, Escape cierra y restaura foco; sin Favoritos falsos', async () => {
    stubSapFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))
    await screen.findByText('NEXORA — Gestión empresarial', undefined, { timeout: 5000 })

    expect(screen.queryByRole('menuitem', { name: 'Favoritos' })).not.toBeInTheDocument()
    for (const label of ['Sistema', 'Editar', 'Navegar', 'Extras', 'Ayuda']) {
      expect(screen.getByRole('menuitem', { name: label })).toBeInTheDocument()
    }

    const sistema = screen.getByRole('menuitem', { name: 'Sistema' })
    await user.click(sistema)
    const menu = await screen.findByRole('menu', { name: 'Sistema' }, { timeout: 5000 })
    expect(within(menu).getByRole('menuitem', { name: /Preferencias de apariencia/ })).toBeInTheDocument()

    // ArrowRight cambia al menú Editar.
    await user.keyboard('{ArrowRight}')
    expect(await screen.findByRole('menu', { name: 'Editar' }, { timeout: 5000 })).toBeInTheDocument()
    expect(screen.queryByRole('menu', { name: 'Sistema' })).not.toBeInTheDocument()

    await user.keyboard('{Escape}')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    // El foco vuelve al botón del menú que estaba abierto (Editar).
    expect(screen.getByRole('menuitem', { name: 'Editar' })).toHaveFocus()
    expect(sistema).not.toHaveFocus()
  })

    it('Navegar contiene únicamente rutas permitidas y navega de verdad', async () => {
    stubSapFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))
    await screen.findByText('NEXORA — Gestión empresarial', undefined, { timeout: 5000 })

    await user.click(screen.getByRole('menuitem', { name: 'Navegar' }))
    const menu = await screen.findByRole('menu', { name: 'Navegar' }, { timeout: 5000 })
    expect(within(menu).getByRole('menuitem', { name: /Tesorería/ })).toBeInTheDocument()
    expect(within(menu).queryByRole('menuitem', { name: /Leads/ })).not.toBeInTheDocument()

    await user.click(within(menu).getByRole('menuitem', { name: /Tesorería/ }))
    await waitFor(() => {
      expect(document.querySelector('.nx-sap-screen__title')?.textContent).toBe('Tesorería')
    })
  })

    it('Extras abre la búsqueda global real y Editar abre Edición protegida real', async () => {
    stubSapFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))
    await screen.findByText('NEXORA — Gestión empresarial', undefined, { timeout: 5000 })

    await user.click(screen.getByRole('menuitem', { name: 'Extras' }))
    await user.click(await screen.findByRole('menuitem', { name: /Búsqueda global/ }, { timeout: 5000 }))
    expect(await screen.findByPlaceholderText(/Ir a…/i, undefined, { timeout: 5000 })).toBeInTheDocument()
    await user.keyboard('{Escape}')

    await user.click(screen.getByRole('menuitem', { name: 'Editar' }))
    await user.click(await screen.findByRole('menuitem', { name: /Edición protegida/ }, { timeout: 5000 }))
    expect(await screen.findByRole('dialog', { name: 'Desbloquear edición' }, { timeout: 5000 })).toBeInTheDocument()
  })
})

describe('SapWorkstation — command field real', () => {
  it('busca módulos locales, Enter navega, Escape limpia; sin transacciones SAP falsas', async () => {
    stubSapFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))
    await screen.findByText('NEXORA — Gestión empresarial', undefined, { timeout: 5000 })

    const command = screen.getByLabelText('Comando: buscar módulo, documento o acción')
    await user.click(command)
    await user.type(command, 'tesorería')
    const listbox = await screen.findByRole('listbox', { name: 'Resultados del comando' }, { timeout: 5000 })
    expect(within(listbox).getByRole('option', { name: /Tesorería/ })).toBeInTheDocument()
    expect(document.body.textContent).not.toMatch(/\/nFB60|ME21N|F110/)

    await user.keyboard('{Enter}')
    await waitFor(() => {
      expect(document.querySelector('.nx-sap-screen__title')?.textContent).toBe('Tesorería')
    })
  })

  it('muestra estado vacío honesto y respeta permisos', async () => {
    stubSapFetch()
    const user = userEvent.setup()
    render(renderApp('/inicio'))
    await screen.findByText('NEXORA — Gestión empresarial', undefined, { timeout: 5000 })

    const command = screen.getByLabelText('Comando: buscar módulo, documento o acción')
    await user.click(command)
    await user.type(command, 'leads inexistentes zzz')
    expect(await screen.findByText(/Sin resultados para/, undefined, { timeout: 5000 })).toBeInTheDocument()

    await user.clear(command)
    await user.type(command, 'leads')
    // 'Leads' requiere permiso CRM ausente: no aparece ni como local.
    await waitFor(() => {
      expect(screen.queryByRole('option', { name: /^Leads$/ })).not.toBeInTheDocument()
    })
  })
})

describe('SapWorkstation — anatomía, screen frame y status bar', () => {
  it('expone datasets estructurales y el screen frame titula la pantalla real', async () => {
    stubSapFetch('sap-gui-horizon')
    render(renderApp('/inicio'))
    await screen.findByText('NEXORA — Gestión empresarial', undefined, { timeout: 5000 })

    const root = document.documentElement.dataset
    expect(root.nxFamily).toBe('sap-gui')
    expect(root.nxAnatomy).toBe('sap-gui-horizon')
    expect(root.nxSapVariant).toBe('horizon')
    expect(root.nxShell).toBe('workstation')
    expect(root.nxNavigation).toBe('tree')
    expect(root.nxMenubar).toBe('classic-modern')
    expect(root.nxCommandbar).toBe('sap-command')
    expect(root.nxToolbar).toBe('horizon')
    expect(root.nxScreen).toBe('work-screen')
    expect(root.nxTabs).toBe('modern-folder')
    expect(root.nxPanel).toBe('modern-titled-box')
    expect(root.nxField).toBe('horizon-compact')
    expect(root.nxButton).toBe('horizon-tool')
    expect(root.nxTable).toBe('enterprise-grid')
    expect(root.nxDialog).toBe('horizon-window')
    expect(root.nxStatusbar).toBe('context')

    expect(document.querySelector('.nx-sap-screen__title')?.textContent).toBe('Inicio')
    expect(screen.getByLabelText('Campo de comandos SAP GUI')).toBeInTheDocument()
    expect(screen.getByRole('toolbar', { name: 'Barra de herramientas SAP GUI' })).toBeInTheDocument()
  })

  it('la status bar muestra contexto real: compañía, vista, período, edición y usuario', async () => {
    stubSapFetch()
    render(renderApp('/inicio'))
    const status = await screen.findByRole('status', { name: 'Contexto SAP GUI' }, { timeout: 5000 })
    expect(within(status).getByText('Listo')).toBeInTheDocument()
    expect(within(status).getByText('Constructora Nexora')).toBeInTheDocument()
    expect(within(status).getByText('Vista empresa · sin proyecto')).toBeInTheDocument()
    expect(within(status).getByText(/Período 2026 · P01 · Abierto/)).toBeInTheDocument()
    expect(within(status).getByText('Edición bloqueada')).toBeInTheDocument()
    expect(within(status).getByText('Administradora')).toBeInTheDocument()
  })

  it('al salir a una familia moderna no quedan datasets SAP residuales', async () => {
    setViewport(1440)
    stubSapFetch('quartz-light')
    render(renderApp('/inicio'))
    await waitFor(() => expect(document.documentElement.dataset.nxFamily).toBe('quartz'), { timeout: 5000 })
    expect(document.documentElement.dataset.nxSapVariant).toBeUndefined()
    expect(screen.queryByRole('menubar', { name: 'Barra de menús SAP GUI' })).not.toBeInTheDocument()
  })

  it('cambiar entre variantes SAP no reconfirma y actualiza la anatomía', async () => {
    setViewport(1440)
    // Parte de un tema moderno: entrar a SAP GUI sí pide confirmación.
    stubSapFetch(null)
    const user = userEvent.setup()
    render(renderApp('/control/configuracion'))
    await screen.findByText('Apariencia (Theme Engine)', undefined, { timeout: 5000 })

    await user.selectOptions(screen.getByLabelText('Familia'), 'sap-gui')
    await user.click(await screen.findByRole('button', { name: 'Cambiar a SAP GUI' }, { timeout: 5000 }))
    await waitFor(() => expect(document.documentElement.dataset.nxTheme).toBe('sap-gui-signature'))

    await user.selectOptions(screen.getByLabelText('Variante'), 'sap-gui-horizon-dark')
    expect(screen.queryByRole('dialog', { name: 'Cambiar a SAP GUI' })).not.toBeInTheDocument()
    await waitFor(() => {
      expect(document.documentElement.dataset.nxTheme).toBe('sap-gui-horizon-dark')
      expect(document.documentElement.dataset.nxAnatomy).toBe('sap-gui-horizon-dark')
      expect(document.documentElement.dataset.nxToolbar).toBe('horizon-dark')
    })
  })
})
