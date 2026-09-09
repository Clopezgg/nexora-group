import { useMemo, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { filterNavGroups } from '../app/navigation'
import { Icon } from '../design-system'
import { useAuth } from '../features/auth/auth-context'
import { useTheme } from '../theme/theme-context'
import { SapEasyAccessTree } from './sap/SapEasyAccessTree'

interface NavListProps {
  onNavigate?: () => void
  /** 'drawer' añade buscador de módulos y secciones colapsables (móvil). */
  variant?: 'sidebar' | 'drawer'
}

/**
 * NavList moderna (sidebar/drawer). En modo SAP GUI delega al árbol
 * SapEasyAccessTree real (estado de expansión por grupo, ARIA viva,
 * teclado completo) en lugar del <details open> forzado.
 */
export function NavList({ onNavigate, variant = 'sidebar' }: NavListProps) {
  const { user } = useAuth()
  const [query, setQuery] = useState('')
  const { activeFamily } = useTheme()
  const isSapGui = activeFamily === 'sap-gui'
  const groups = useMemo(() => filterNavGroups(user?.permissions), [user?.permissions])

  if (isSapGui) {
    return <SapEasyAccessTree variant={variant === 'drawer' ? 'drawer' : 'sidebar'} onNavigate={onNavigate} />
  }

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
