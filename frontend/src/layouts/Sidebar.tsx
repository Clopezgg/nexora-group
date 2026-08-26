import { NavList } from './NavList'

export function Sidebar() {
  return (
    <aside className="nx-sidebar">
      <div className="nx-sidebar__brand">NEXORA</div>
      <NavList />
    </aside>
  )
}
