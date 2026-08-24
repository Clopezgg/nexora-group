import { useMemo, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { NavList } from './NavList'
import { navGroups } from '../app/navigation'
import { CommandPalette, Drawer, type CommandItem } from '../design-system'
import './AppLayout.css'

export function AppLayout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  const commandItems = useMemo<CommandItem[]>(
    () =>
      navGroups.flatMap((group) =>
        group.items.map((item) => ({
          id: item.path,
          label: item.label,
          group: group.label,
          path: item.path,
        })),
      ),
    [],
  )

  return (
    <div className="nx-app-shell">
      <Sidebar />
      <div className="nx-app-shell__main">
        <Topbar onOpenNav={() => setMobileNavOpen(true)} />
        <main className="nx-app-shell__content">
          <Outlet />
        </main>
      </div>
      <Drawer
        open={mobileNavOpen}
        title="Navegación"
        side="left"
        onClose={() => setMobileNavOpen(false)}
      >
        <NavList onNavigate={() => setMobileNavOpen(false)} />
      </Drawer>
      <CommandPalette items={commandItems} />
    </div>
  )
}
