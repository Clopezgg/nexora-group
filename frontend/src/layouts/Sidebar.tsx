import { NavList } from './NavList'

export function Sidebar() {
  return (
    <aside className="nx-sidebar">
      <div className="nx-sidebar__brand" aria-label="NEXORA">
        <span className="nx-sidebar__brand-mark" aria-hidden="true" />
        <span className="nx-sidebar__brand-copy">
          <span className="nx-sidebar__brand-name">NEXORA</span>
          <span className="nx-sidebar__brand-tagline">Gestión financiera para construcción</span>
        </span>
      </div>
      <NavList />
    </aside>
  )
}
