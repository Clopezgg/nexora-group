import { useMemo, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { filterNavGroups } from '../app/navigation'
import { Icon } from '../design-system'
import { useAuth } from '../features/auth/auth-context'

interface NavListProps {
  onNavigate?: () => void
  /** 'drawer' añade buscador de módulos y secciones colapsables (móvil). */
  variant?: 'sidebar' | 'drawer'
}

/**
 * NavList del shell moderno (sidebar/drawer). SAP GUI usa su propia
 * SapWorkstation y nunca atraviesa esta composición.
 */
export function NavList({ onNavigate, variant = 'sidebar' }: NavListProps) {
  const { user } = useAuth()
  const [query, setQuery] = useState('')
  const groups = useMemo(() => filterNavGroups(user?.permissions), [user?.permissions])

  const normalized = query.trim().toLowerCase()
  const filteredGroups = normalized
    ? groups
        .map((group) => ({
          ...group,
          items: group.items.filter((item) => item.label.toLowerCase().includes(normalized)),
        }))
        .filter((group) => group.items.length > 0)
    : groups

  const isDrawer = variant === 'drawer'

  return (
    <nav className="nx-sidebar__nav" aria-label="Navegación principal">
      {isDrawer ? (
        <input
          type="search"
          className="nx-sidebar__search"
          placeholder="Buscar módulo…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          aria-label="Buscar módulo"
        />
      ) : null}

      {filteredGroups.map((group) => (
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
