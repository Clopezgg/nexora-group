import { NavLink } from 'react-router-dom'
import { filterNavGroups } from '../app/navigation'
import { Icon } from '../design-system'
import { useAuth } from '../features/auth/auth-context'

export function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth()
  const groups = filterNavGroups(user?.permissions)

  return (
    <nav className="nx-sidebar__nav" aria-label="Navegación principal">
      {groups.map((group) => (
        <div key={group.key} className="nx-sidebar__group">
          <p className="nx-sidebar__group-label">{group.label}</p>
          <ul className="nx-sidebar__list">
            {group.items.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  end
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    ['nx-sidebar__link', isActive ? 'nx-sidebar__link--active' : '']
                      .filter(Boolean)
                      .join(' ')
                  }
                >
                  <Icon name={item.icon} />
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
