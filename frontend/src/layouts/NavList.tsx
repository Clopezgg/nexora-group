import { useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { filterNavGroups } from '../app/navigation'
import { Icon } from '../design-system'
import { useAuth } from '../features/auth/auth-context'

interface NavListProps {
  onNavigate?: () => void
  /** 'drawer' añade buscador de módulos y secciones colapsables (móvil). */
  variant?: 'sidebar' | 'drawer'
}

export function NavList({ onNavigate, variant = 'sidebar' }: NavListProps) {
  const { user } = useAuth()
  const location = useLocation()
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

      {filteredGroups.map((group) => {
        const hasActive = group.items.some((item) => location.pathname.startsWith(item.path))
        const list = (
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
        )

        if (isDrawer) {
          return (
            <details
              key={group.key}
              className="nx-sidebar__group nx-sidebar__group--collapsible"
              open={hasActive || Boolean(normalized)}
            >
              <summary className="nx-sidebar__group-label">{group.label}</summary>
              {list}
            </details>
          )
        }

        return (
          <div key={group.key} className="nx-sidebar__group">
            <p className="nx-sidebar__group-label">{group.label}</p>
            {list}
          </div>
        )
      })}
    </nav>
  )
}
