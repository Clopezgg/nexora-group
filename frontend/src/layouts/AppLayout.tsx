import { useMemo, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { NavList } from './NavList'
import { BottomNav } from './BottomNav'
import { filterNavGroups } from '../app/navigation'
import { Button, CommandPalette, Drawer, type CommandItem } from '../design-system'
import { useAuth } from '../features/auth/auth-context'
import { useActiveCompany } from '../hooks/useActiveCompany'
import { globalSearch } from '../services/searchService'
import './AppLayout.css'

export function AppLayout() {
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

  return (
    <div className="nx-app-shell">
      <Sidebar />
      <div className="nx-app-shell__main">
        <Topbar onOpenNav={() => setMobileNavOpen(true)} />
        <main className="nx-app-shell__content">
          <Outlet />
        </main>
      </div>
      <BottomNav onOpenMore={() => setMobileNavOpen(true)} />
      <Drawer
        open={mobileNavOpen}
        title="Navegación"
        side="left"
        onClose={() => setMobileNavOpen(false)}
      >
        <NavList variant="drawer" onNavigate={() => setMobileNavOpen(false)} />
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
