import { NavLink } from 'react-router-dom'
import { navItems } from '../app/navigation'

export function Sidebar() {
  return (
    <nav className="nx-sidebar" aria-label="Navegación principal">
      <div className="nx-sidebar__brand">NEXORA</div>
      <ul className="nx-sidebar__list">
        {navItems.map((item) => (
          <li key={item.path}>
            <NavLink
              to={item.path}
              className={({ isActive }) =>
                ['nx-sidebar__link', isActive ? 'nx-sidebar__link--active' : '']
                  .filter(Boolean)
                  .join(' ')
              }
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
