import { useMemo, useState } from 'react'
import { useAuth } from '../../features/auth/auth-context'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { filterNavGroups } from '../../app/navigation'
import { Button, Drawer, type CommandItem } from '../../design-system'
import { CommandPalette } from '../../design-system/primitives/CommandPalette'
import { Topbar } from '../Topbar'
import { globalSearch } from '../../services/searchService'
import { SapTitleBar } from './SapTitleBar'
import { SapMenuBar } from './SapMenuBar'
import { SapCommandBar } from './SapCommandBar'
import { SapToolbar } from './SapToolbar'
import { SapEasyAccessTree } from './SapEasyAccessTree'
import { SapScreenFrame } from './SapScreenFrame'
import { SapStatusBar } from './SapStatusBar'

/**
 * SapWorkstation: COMPOSICIÓN DE PRESENTACIÓN, no otra app.
 * Reutiliza Outlet (vía SapScreenFrame), compañía/proyecto activos, período
 * fiscal, Protected Edit, usuario, notifications, command palette,
 * globalSearch, route definitions, permission filtering, logout y drawer
 * responsive. No duplica Router, auth ni permisos.
 */
export function SapWorkstation() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const { activeCompanyId } = useActiveCompany()
  const { user, logout } = useAuth()
  const visibleGroups = useMemo(() => filterNavGroups(user?.permissions), [user?.permissions])

  const commandItems = useMemo<CommandItem[]>(
    () =>
      visibleGroups.flatMap((group) =>
        group.items.map((item) => ({
          id: item.path,
          label: item.label,
          group: group.label,
          path: item.path,
        })),
      ),
    [visibleGroups],
  )

  const searchRemote = useMemo(() => {
    if (!activeCompanyId) return undefined
    const companyId = activeCompanyId
    return async (query: string): Promise<CommandItem[]> => {
      const results = await globalSearch(companyId, query)
      return results.map((result) => ({
        id: result.id,
        label: result.label,
        group: result.group,
        path: result.path,
      }))
    }
  }, [activeCompanyId])

  const openSearch = () => {
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }))
  }

  return (
    <div className="nx-app-shell nx-app-shell--sap">
      <SapTitleBar />
      <SapMenuBar groups={visibleGroups} onOpenSearch={openSearch} onOpenNav={() => setMobileNavOpen(true)} />
      <div className="nx-sap-commandrow">
        <SapCommandBar items={commandItems} searchRemote={searchRemote} />
        <SapToolbar onOpenNav={() => setMobileNavOpen(true)} />
      </div>
      <aside className="nx-sidebar" aria-label="SAP Easy Access">
        <div className="nx-sidebar__brand" aria-label="SAP Easy Access">
          <span className="nx-sidebar__brand-mark" aria-hidden="true" />
          <span className="nx-sidebar__brand-copy">
            <span className="nx-sidebar__brand-name">SAP Easy Access</span>
            <span className="nx-sidebar__brand-tagline">Navegación de Nexora</span>
          </span>
        </div>
        <SapEasyAccessTree variant="sidebar" />
      </aside>
      <div className="nx-app-shell__main">
        <Topbar onOpenNav={() => setMobileNavOpen(true)} />
        <main className="nx-app-shell__content">
          <SapScreenFrame />
        </main>
      </div>
      <SapStatusBar />
      <Drawer
        open={mobileNavOpen}
        title="Navegación"
        side="left"
        onClose={() => setMobileNavOpen(false)}
      >
        <SapEasyAccessTree variant="drawer" onNavigate={() => setMobileNavOpen(false)} />
        <div className="nx-drawer__footer">
          <div className="nx-drawer__user">
            <span className="nx-drawer__user-name">{user?.fullName ?? user?.email}</span>
            {user?.roles?.[0] ? (
              <span className="nx-drawer__user-role">{user.roles[0]}</span>
            ) : null}
          </div>
          <Button
            variant="secondary"
            onClick={() => {
              setMobileNavOpen(false)
              logout()
            }}
          >
            Cerrar sesión
          </Button>
        </div>
      </Drawer>
      <CommandPalette items={commandItems} searchRemote={searchRemote} />
    </div>
  )
}
