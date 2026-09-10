import { useEffect, useMemo, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../features/auth/auth-context'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useActiveContext } from '../../features/context/useActiveContext'
import type { SapMenuBarProps } from './sapWorkstation.types'

interface MenuEntry {
  id: string
  label: string
  hint?: string
  action: () => void
  disabled?: boolean
}

/**
 * Menu bar SAP real: Sistema / Editar / Navegar / Extras / Ayuda.
 * Cada entrada ejecuta una función real de Nexora (navegación RBAC,
 * compañía/proyecto, búsqueda, Protected Edit, logout). No hay acciones
 * falsas ni Favoritos inventados: sin persistencia de favoritos no hay menú
 * Favoritos. Teclado completo: Escape, ArrowLeft/Right/Up/Down, Enter.
 */
export function SapMenuBar({ groups, onOpenSearch, onOpenNav }: SapMenuBarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const { activeCompany } = useActiveCompany()
  const { context } = useActiveContext()
  const [openMenu, setOpenMenu] = useState<string | null>(null)
  const [focusIndex, setFocusIndex] = useState(0)
  const barRef = useRef<HTMLElement>(null)
  const grants = useMemo(() => new Set(user?.permissions ?? []), [user?.permissions])
  const can = (...permissions: string[]) => permissions.some((permission) => grants.has(permission))

  const openEditAccess = () => {
    window.dispatchEvent(new CustomEvent('nexora:edit-access-required'))
  }

  const focusCompanySelect = () => {
    onOpenNav()
    requestAnimationFrame(() => {
      document.querySelector<HTMLElement>('.nx-topbar__company select, .nx-topbar__company [aria-label="Empresa activa"]')?.focus()
    })
  }

  const focusProjectSelect = () => {
    onOpenNav()
    requestAnimationFrame(() => {
      document.querySelector<HTMLElement>('.nx-topbar__context select, .nx-topbar__context [aria-label="Proyecto seleccionado"]')?.focus()
    })
  }

  const menus: Array<{ id: string; label: string; entries: MenuEntry[] }> = [
    {
      id: 'sistema',
      label: 'Sistema',
      entries: [
        { id: 'inicio', label: 'Inicio', action: () => navigate('/inicio') },
        {
          id: 'compania',
          label: `Cambiar compañía${activeCompany ? ` · ${activeCompany.name}` : ''}`,
          action: focusCompanySelect,
        },
        {
          id: 'proyecto',
          label: context.activeProjectId ? 'Cambiar proyecto / vista' : 'Seleccionar proyecto',
          action: focusProjectSelect,
        },
        { id: 'preferencias', label: 'Preferencias de apariencia', action: () => navigate('/control/configuracion') },
        { id: 'salir', label: `Cerrar sesión (${user?.fullName ?? user?.email ?? 'usuario'})`, action: () => logout() },
      ],
    },
    {
      id: 'editar',
      label: 'Editar',
      entries: [
        { id: 'protected-edit', label: 'Edición protegida…', hint: 'token temporal', action: openEditAccess },
        ...(can('workflow.approval:read')
          ? [{ id: 'aprobaciones', label: 'Aprobaciones pendientes', action: () => navigate('/inicio/aprobaciones') }]
          : []),
      ],
    },
    {
      id: 'navegar',
      label: 'Navegar',
      entries: groups.flatMap((group) =>
        group.items.map((item) => ({
          id: item.path,
          label: `${group.label} · ${item.label}`,
          action: () => navigate(item.path),
          disabled: false,
        })),
      ),
    },
    {
      id: 'extras',
      label: 'Extras',
      entries: [
        { id: 'buscar', label: 'Búsqueda global…', hint: 'Cmd/Ctrl + K', action: onOpenSearch },
        ...(can('document.document:read')
          ? [{ id: 'documentos', label: 'Documentos', action: () => navigate('/control/documentos') }]
          : []),
        ...(can('audit.log:read')
          ? [{ id: 'auditoria', label: 'Auditoría', action: () => navigate('/control/auditoria') }]
          : []),
      ],
    },
    {
      id: 'ayuda',
      label: 'Ayuda',
      entries: [
        { id: 'atajos', label: 'Atajos de teclado…', hint: 'Cmd/Ctrl + K', action: onOpenSearch },
        {
          id: 'pantalla',
          label: `Esta pantalla · ${location.pathname}`,
          action: () => navigate('/control/configuracion'),
        },
        { id: 'version', label: 'Versión y compilación', action: () => navigate('/control/configuracion') },
      ],
    },
  ]

  // Cerrar con Escape global + clic fuera; restaurar foco al botón del menú.
  useEffect(() => {
    if (!openMenu) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        setOpenMenu(null)
        barRef.current?.querySelector<HTMLElement>(`[data-menu-button="${openMenu}"]`)?.focus()
      }
    }
    const onPointer = (event: PointerEvent) => {
      if (!barRef.current?.contains(event.target as Node)) setOpenMenu(null)
    }
    document.addEventListener('keydown', onKey)
    document.addEventListener('pointerdown', onPointer)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.removeEventListener('pointerdown', onPointer)
    }
  }, [openMenu])

  const activeEntries = menus.find((menu) => menu.id === openMenu)?.entries ?? []

  const onBarKeyDown = (event: React.KeyboardEvent) => {
    const buttons = Array.from(barRef.current?.querySelectorAll<HTMLElement>('[data-menu-button]') ?? [])
    const current = buttons.findIndex((button) => button === document.activeElement)
    if (event.key === 'ArrowRight') {
      event.preventDefault()
      const next = buttons[(current + 1 + buttons.length) % buttons.length]
      next?.focus()
      if (openMenu && next) setOpenMenu(next.dataset.menuButton ?? null)
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault()
      const prev = buttons[(current - 1 + buttons.length) % buttons.length]
      prev?.focus()
      if (openMenu && prev) setOpenMenu(prev.dataset.menuButton ?? null)
    } else if ((event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') && current >= 0) {
      const id = buttons[current]?.dataset.menuButton
      if (id && openMenu !== id) {
        event.preventDefault()
        setOpenMenu(id)
        setFocusIndex(0)
        requestAnimationFrame(() => {
          barRef.current?.querySelector<HTMLElement>(`[data-menu-item="0"]`)?.focus()
        })
      }
    }
  }

  const onMenuKeyDown = (event: React.KeyboardEvent, index: number) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      const next = (index + 1) % activeEntries.length
      setFocusIndex(next)
      barRef.current?.querySelector<HTMLElement>(`[data-menu-item="${next}"]`)?.focus()
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      const prev = (index - 1 + activeEntries.length) % activeEntries.length
      setFocusIndex(prev)
      barRef.current?.querySelector<HTMLElement>(`[data-menu-item="${prev}"]`)?.focus()
    } else if (event.key === 'Home') {
      event.preventDefault()
      setFocusIndex(0)
      barRef.current?.querySelector<HTMLElement>(`[data-menu-item="0"]`)?.focus()
    } else if (event.key === 'End') {
      event.preventDefault()
      setFocusIndex(activeEntries.length - 1)
      barRef.current?.querySelector<HTMLElement>(`[data-menu-item="${activeEntries.length - 1}"]`)?.focus()
    }
  }

  return (
    <nav
      ref={barRef}
      className="nx-sap-menubar"
      role="menubar"
      aria-label="Barra de menús SAP GUI"
      onKeyDown={onBarKeyDown}
    >
      {menus.map((menu) => (
        <div key={menu.id} className="nx-sap-menu" role="none">
          <button
            type="button"
            role="menuitem"
            aria-haspopup="true"
            aria-expanded={openMenu === menu.id}
            data-menu-button={menu.id}
            className={openMenu === menu.id ? 'nx-sap-menu__button--open' : undefined}
            onClick={() => {
              setOpenMenu((current) => (current === menu.id ? null : menu.id))
              setFocusIndex(0)
            }}
            onMouseEnter={() => {
              if (openMenu) {
                setOpenMenu(menu.id)
                setFocusIndex(0)
              }
            }}
          >
            {menu.label}
          </button>
          {openMenu === menu.id ? (
            <ul className="nx-sap-menu__list" role="menu" aria-label={menu.label}>
              {menu.entries.map((entry, index) => (
                <li key={entry.id} role="none">
                  <button
                    type="button"
                    role="menuitem"
                    data-menu-item={index}
                    tabIndex={index === focusIndex ? 0 : -1}
                    disabled={entry.disabled}
                    onKeyDown={(event) => onMenuKeyDown(event, index)}
                    onClick={() => {
                      setOpenMenu(null)
                      barRef.current?.querySelector<HTMLElement>(`[data-menu-button="${menu.id}"]`)?.focus()
                      entry.action()
                    }}
                  >
                    <span>{entry.label}</span>
                    {entry.hint ? <span className="nx-sap-menu__hint">{entry.hint}</span> : null}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ))}
    </nav>
  )
}
