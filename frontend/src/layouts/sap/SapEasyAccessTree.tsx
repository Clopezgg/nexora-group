import { useMemo, useRef, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { filterNavGroups, type NavGroup } from '../../app/navigation'
import { useAuth } from '../../features/auth/auth-context'
import { Icon } from '../../design-system'
import type { SapTreeProps } from './sapWorkstation.types'

/**
 * Árbol SAP Easy Access con estado real de expansión por grupo.
 * Corrige el defecto `open={isSapGui || ...}` que forzaba todos los grupos
 * abiertos: cada grupo se expande/contrae por interacción del usuario y el
 * rerender nunca reabre a la fuerza. La búsqueda expande temporalmente los
 * resultados y al limpiarla se restaura el estado previo del usuario.
 */
export function SapEasyAccessTree({ variant = 'sidebar', onNavigate }: SapTreeProps) {
  const { user } = useAuth()
  const location = useLocation()
  const [query, setQuery] = useState('')
  const [expanded, setExpanded] = useState<Record<string, boolean> | null>(null)
  const [focusIndex, setFocusIndex] = useState(0)
  const [typeahead, setTypeahead] = useState('')
  const treeRef = useRef<HTMLElement>(null)
  const typeaheadTimer = useRef<number | undefined>(undefined)
  const isDrawer = variant === 'drawer'

  const groups = useMemo(() => filterNavGroups(user?.permissions), [user?.permissions])
  const normalized = query.trim().toLowerCase()
  const searching = normalized.length > 0

  const filteredGroups: NavGroup[] = searching
    ? groups
        .map((group) => ({
          ...group,
          items: group.items.filter((item) => item.label.toLowerCase().includes(normalized)),
        }))
        .filter((group) => group.items.length > 0)
    : groups

  // Estado inicial: solo el grupo con la ruta activa abierto. Lazy init para
  // que ningún rerender lo reabra a la fuerza.
  const [initialExpanded] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {}
    for (const group of groups) {
      init[group.key] = group.items.some((item) => location.pathname.startsWith(item.path))
    }
    return init
  })
  const effectiveExpanded = expanded ?? initialExpanded

  const onSearchChange = (value: string) => {
    setQuery(value)
    // Al limpiar la búsqueda se restaura el comportamiento coherente previo.
    if (value.trim().length === 0) setFocusIndex(0)
  }

  const toggleGroup = (key: string) => {
    setExpanded((prev) => {
      const base = prev ?? initialExpanded
      return { ...base, [key]: !base[key] }
    })
  }

  const visibleItems = useMemo(() => {
    const list: Array<{ kind: 'group' | 'link'; groupKey: string; label: string; path?: string }> = []
    for (const group of filteredGroups) {
      const open = searching ? true : (effectiveExpanded[group.key] ?? false)
      list.push({ kind: 'group', groupKey: group.key, label: group.label })
      if (open) {
        for (const item of group.items) {
          list.push({ kind: 'link', groupKey: group.key, label: item.label, path: item.path })
        }
      }
    }
    return list
  }, [filteredGroups, searching, effectiveExpanded])

  const focusItem = (index: number) => {
    const count = visibleItems.length
    if (count === 0) return
    const next = ((index % count) + count) % count
    setFocusIndex(next)
    requestAnimationFrame(() => {
      treeRef.current?.querySelectorAll<HTMLElement>('[role="treeitem"]')[next]?.focus()
    })
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLElement>) => {
    const target = (event.target as HTMLElement).closest<HTMLElement>('[role="treeitem"]')
    if (!target) return
    const groupKey = target.dataset.groupKey
    const kind = target.dataset.kind
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      focusItem(focusIndex + 1)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      focusItem(focusIndex - 1)
    } else if (event.key === 'Home') {
      event.preventDefault()
      focusItem(0)
    } else if (event.key === 'End') {
      event.preventDefault()
      focusItem(visibleItems.length - 1)
    } else if (event.key === 'ArrowRight') {
      if (kind === 'group' && groupKey && !searching) {
        event.preventDefault()
        if (!effectiveExpanded[groupKey]) toggleGroup(groupKey)
        else focusItem(focusIndex + 1)
      }
    } else if (event.key === 'ArrowLeft') {
      if (kind === 'group' && groupKey && !searching && effectiveExpanded[groupKey]) {
        event.preventDefault()
        toggleGroup(groupKey)
      } else if (kind === 'link') {
        event.preventDefault()
        const groupIndex = visibleItems.findIndex(
          (item, index) => index < focusIndex && item.kind === 'group' && item.groupKey === groupKey,
        )
        if (groupIndex >= 0) focusItem(groupIndex)
      }
    } else if ((event.key === 'Enter' || event.key === ' ') && kind === 'group' && groupKey && !searching) {
      // Los links usan NavLink nativo: Enter/Space navegan por defecto.
      if ((event.target as HTMLElement).tagName !== 'A') {
        event.preventDefault()
        toggleGroup(groupKey)
      }
    } else if (event.key.length === 1 && /[\p{L}\p{N}]/u.test(event.key)) {
      // Typeahead por letra inicial sobre etiquetas visibles.
      const next = typeahead + event.key.toLowerCase()
      setTypeahead(next)
      window.clearTimeout(typeaheadTimer.current)
      typeaheadTimer.current = window.setTimeout(() => setTypeahead(''), 600)
      const match = visibleItems.findIndex((item) => item.label.toLowerCase().startsWith(next))
      if (match >= 0) {
        event.preventDefault()
        focusItem(match)
      }
    }
  }

  const flatIndex = (groupKey: string, path?: string) =>
    visibleItems.findIndex(
      (entry) => entry.groupKey === groupKey && (path ? entry.path === path : entry.kind === 'group'),
    )

  return (
    <nav
      ref={treeRef}
      className="nx-sidebar__nav nx-sap-tree"
      aria-label="Navegación principal"
      role="tree"
      aria-multiselectable="false"
      onKeyDown={handleKeyDown}
    >
      {isDrawer ? (
        <input
          type="search"
          className="nx-sidebar__search"
          placeholder="Buscar módulo…"
          value={query}
          onChange={(event) => onSearchChange(event.target.value)}
          aria-label="Buscar módulo"
        />
      ) : null}

      {filteredGroups.length === 0 ? (
        <p className="nx-sidebar__empty" role="status">Sin módulos coincidentes.</p>
      ) : null}

      {filteredGroups.map((group) => {
        const open = searching ? true : (effectiveExpanded[group.key] ?? false)
        const groupFlatIndex = flatIndex(group.key)
        return (
          <div key={group.key} className="nx-sidebar__group nx-sidebar__group--collapsible" role="none">
            <div
              className="nx-sidebar__group-label"
              role="treeitem"
              aria-expanded={open}
              aria-selected="false"
              aria-level={1}
              tabIndex={groupFlatIndex === focusIndex ? 0 : -1}
              data-group-key={group.key}
              data-kind="group"
              onClick={() => {
                if (!searching) toggleGroup(group.key)
              }}
              onFocus={() => {
                if (groupFlatIndex >= 0) setFocusIndex(groupFlatIndex)
              }}
            >
              {group.label}
            </div>
            {open ? (
              <ul className="nx-sidebar__list" role="group" aria-label={group.label}>
                {group.items.map((item) => {
                  const linkFlatIndex = flatIndex(group.key, item.path)
                  const selected = location.pathname === item.path || location.pathname.startsWith(`${item.path}/`)
                  return (
                    <li key={item.path} role="none">
                      <NavLink
                        to={item.path}
                        end={false}
                        role="treeitem"
                        aria-level={2}
                        aria-selected={selected}
                        aria-current={selected ? 'page' : undefined}
                        tabIndex={linkFlatIndex === focusIndex ? 0 : -1}
                        data-group-key={group.key}
                        data-kind="link"
                        onClick={onNavigate}
                        onFocus={() => {
                          if (linkFlatIndex >= 0) setFocusIndex(linkFlatIndex)
                        }}
                        className={({ isActive }) =>
                          ['nx-sidebar__link', isActive || selected ? 'nx-sidebar__link--active' : '']
                            .filter(Boolean)
                            .join(' ')
                        }
                      >
                        <Icon name={item.icon} />
                        {item.label}
                      </NavLink>
                    </li>
                  )
                })}
              </ul>
            ) : null}
          </div>
        )
      })}
    </nav>
  )
}
