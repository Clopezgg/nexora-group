import { NavLink } from 'react-router-dom'
import { navGroups } from '../app/navigation'

export function NavList({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="nx-sidebar__nav" aria-label="Navegación principal">
      {navGroups.map((group) => (
        <div key={group.key} className="nx-sidebar__group">
          <p className="nx-sidebar__group-label">{group.label}</p>
          <ul className="nx-sidebar__list">
            {group.items.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  onClick={onNavigate}
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
        </div>
      ))}
    </nav>
  )
}
