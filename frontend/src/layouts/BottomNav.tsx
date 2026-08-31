import { NavLink } from 'react-router-dom'
import { Icon, type IconName } from '../design-system'
import { useAuth } from '../features/auth/auth-context'

interface BottomNavProps {
  onOpenMore: () => void
  onQuickCreate: () => void
}

interface BottomNavItem {
  path: string
  label: string
  icon: IconName
  requiredAny?: string[]
}

/** Candidatos para los 2 slots laterales de la navegación inferior móvil.
 * "Finanzas" y "Proyectos" son la composición aprobada (Opción 2); se
 * filtran por RBAC y se completan con alternativas si faltan permisos. */
const CANDIDATES: BottomNavItem[] = [
  { path: '/finanzas/control', label: 'Finanzas', icon: 'bank', requiredAny: ['treasury.account:read', 'accounting.journal_entry:read'] },
  { path: '/proyectos', label: 'Proyectos', icon: 'project', requiredAny: ['project:read'] },
  { path: '/inicio/aprobaciones', label: 'Mi trabajo', icon: 'clipboard', requiredAny: ['workflow.approval:read'] },
  { path: '/finanzas/tesoreria', label: 'Tesorería', icon: 'card', requiredAny: ['treasury.account:read'] },
  { path: '/control/reportes', label: 'Reportes', icon: 'file', requiredAny: ['reports.trial_balance:read', 'reports.general_ledger:read'] },
]

function Slot({ item }: { item: BottomNavItem }) {
  return (
    <NavLink
      to={item.path}
      className={({ isActive }) =>
        ['nx-bottom-nav__item', isActive ? 'nx-bottom-nav__item--active' : ''].filter(Boolean).join(' ')
      }
    >
      <Icon name={item.icon} />
      <span>{item.label}</span>
    </NavLink>
  )
}

export function BottomNav({ onOpenMore, onQuickCreate }: BottomNavProps) {
  const { user } = useAuth()
  const grants = new Set(user?.permissions ?? [])
  const sides = CANDIDATES.filter(
    (item) => !item.requiredAny || item.requiredAny.some((permission) => grants.has(permission)),
  ).slice(0, 2)

  return (
    <nav className="nx-bottom-nav" aria-label="Navegación principal (móvil)">
      <NavLink
        to="/inicio"
        end
        className={({ isActive }) =>
          ['nx-bottom-nav__item', isActive ? 'nx-bottom-nav__item--active' : ''].filter(Boolean).join(' ')
        }
      >
        <Icon name="home" />
        <span>Inicio</span>
      </NavLink>

      {sides[0] ? <Slot item={sides[0]} /> : <span className="nx-bottom-nav__item" aria-hidden="true" />}

      <button
        type="button"
        className="nx-bottom-nav__fab"
        onClick={onQuickCreate}
        aria-label="Crear"
      >
        <Icon name="plus" />
      </button>

      {sides[1] ? <Slot item={sides[1]} /> : <span className="nx-bottom-nav__item" aria-hidden="true" />}

      <button type="button" className="nx-bottom-nav__item" onClick={onOpenMore}>
        <Icon name="menu" />
        <span>Más</span>
      </button>
    </nav>
  )
}
