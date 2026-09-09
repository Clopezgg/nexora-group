import { useMemo, useState, type KeyboardEvent } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { filterNavGroups } from '../app/navigation'
import { Icon } from '../design-system'
import { useAuth } from '../features/auth/auth-context'
import { useTheme } from '../theme/theme-context'

interface NavListProps {
  onNavigate?: () => void
  /** 'drawer' añade buscador de módulos y secciones colapsables (móvil). */
  variant?: 'sidebar' | 'drawer'
}

export function NavList({ onNavigate, variant = 'sidebar' }: NavListProps) {
  const { user } = useAuth()
  const location = useLocation()
  const [query, setQuery] = useState('')
  const { activeFamily } = useTheme()
  const isSapGui = activeFamily === 'sap-gui'
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

  const handleTreeKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (!isSapGui) return
    const target = (event.target as HTMLElement).closest<HTMLElement>('[role="treeitem"]')
    if (!target) return
    const items = Array.from(
      event.currentTarget.querySelectorAll<HTMLElement>('[role="treeitem"]'),
    ).filter((item) => item.offsetParent !== null)
    const currentIndex = items.indexOf(target)
    const details = target.closest('details')
    let next: HTMLElement | undefined
    if (event.key === 'ArrowDown') next = items[currentIndex + 1] ?? items[0]
    if (event.key === 'ArrowUp') next = items[currentIndex - 1] ?? items.at(-1)
    if (event.key === 'Home') next = items[0]
    if (event.key === 'End') next = items.at(-1)
    if (event.key === 'ArrowRight' && details && !details.open) details.open = true
    if (event.key === 'ArrowLeft' && details?.open) details.open = false
    if (next || event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
      event.preventDefault()
      next?.focus()
    }
  }

  return (
    <nav
      className="nx-sidebar__nav"
      aria-label="Navegación principal"
      role={isSapGui ? 'tree' : undefined}
      onKeyDown={handleTreeKeyDown}
    >
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
          <ul className="nx-sidebar__list" role={isSapGui ? 'group' : undefined}>
            {group.items.map((item) => (
              <li key={item.path} role={isSapGui ? 'none' : undefined}>
                <NavLink
                  to={item.path}
                  end
                  role={isSapGui ? 'treeitem' : undefined}
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

        if (isDrawer || isSapGui) {
          return (
            <details
              key={group.key}
              className="nx-sidebar__group nx-sidebar__group--collapsible"
              open={isSapGui || hasActive || Boolean(normalized)}
              role={isSapGui ? 'none' : undefined}
              onToggle={isSapGui ? (event) => {
                event.currentTarget.querySelector('summary')?.setAttribute(
                  'aria-expanded',
                  String(event.currentTarget.open),
                )
              } : undefined}
            >
              <summary
                className="nx-sidebar__group-label"
                role={isSapGui ? 'treeitem' : undefined}
                aria-expanded={isSapGui ? true : undefined}
              >
                {group.label}
              </summary>
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
