import { useMemo, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { NavList } from './NavList'
import { navGroups } from '../app/navigation'
import { CommandPalette, Drawer, type CommandItem } from '../design-system'
import { useActiveCompany } from '../hooks/useActiveCompany'
import { globalSearch } from '../services/searchService'
import './AppLayout.css'

export function AppLayout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const { activeCompanyId } = useActiveCompany()

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

  // Cross-entity global search (NXR-REQ-0092). Undefined (no remote branch)
  // until a company is active -- CommandPalette keeps working as a pure
  // local nav filter in that case, never blank.
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
      <Drawer
        open={mobileNavOpen}
        title="Navegación"
        side="left"
        onClose={() => setMobileNavOpen(false)}
      >
        <NavList onNavigate={() => setMobileNavOpen(false)} />
      </Drawer>
      <CommandPalette items={commandItems} searchRemote={searchRemote} />
    </div>
  )
}
