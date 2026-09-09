import { NavList } from './NavList'
import { useTheme } from '../theme/theme-context'

export function Sidebar() {
  const { activeFamily } = useTheme()
  const isSapGui = activeFamily === 'sap-gui'
  return (
    <aside className="nx-sidebar">
      <div className="nx-sidebar__brand" aria-label="NEXORA">
        <span className="nx-sidebar__brand-mark" aria-hidden="true" />
        <span className="nx-sidebar__brand-copy">
          <span className="nx-sidebar__brand-name">{isSapGui ? 'SAP Easy Access' : 'NEXORA'}</span>
          <span className="nx-sidebar__brand-tagline">{isSapGui ? 'Navegación de Nexora' : 'Gestión financiera para construcción'}</span>
        </span>
      </div>
      <NavList />
    </aside>
  )
}
