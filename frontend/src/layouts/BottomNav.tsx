import { NavLink } from 'react-router-dom'
import { Icon, type IconName } from '../design-system'
import { useAuth } from '../features/auth/auth-context'

interface BottomNavProps {
  onOpenMore: () => void
}

interface BottomNavItem {
  path: string
  label: string
  icon: IconName
  requiredAny?: string[]
}

/** Candidatos para los 3 slots centrales de la navegación inferior móvil.
 * Se filtran por permisos (RBAC) y se toman los primeros disponibles. */
const CANDIDATES: BottomNavItem[] = [
  { path: '/finanzas/control', label: 'Finanzas', icon: 'bank', requiredAny: ['treasury.account:read', 'accounting.journal_entry:read'] },
  { path: '/proyectos', label: 'Proyectos', icon: 'project', requiredAny: ['project:read'] },
  { path: '/inicio/aprobaciones', label: 'Mi trabajo', icon: 'clipboard', requiredAny: ['workflow.approval:read'] },
  { path: '/finanzas/tesoreria', label: 'Tesorería', icon: 'card', requiredAny: ['treasury.account:read'] },
  { path: '/control/reportes', label: 'Reportes', icon: 'file', requiredAny: ['reports.trial_balance:read', 'reports.general_ledger:read'] },
  { path: '/abastecimiento/ordenes-de-compra', label: 'Compras', icon: 'package', requiredAny: ['procurement.purchase_order:read'] },
]

export function BottomNav({ onOpenMore }: BottomNavProps) {
  const { user } = useAuth()
  const grants = new Set(user?.permissions ?? [])
  const middle = CANDIDATES.filter(
    (item) => !item.requiredAny || item.requiredAny.some((permission) => grants.has(permission)),
  ).slice(0, 3)

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

      {middle.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          className={({ isActive }) =>
            ['nx-bottom-nav__item', isActive ? 'nx-bottom-nav__item--active' : ''].filter(Boolean).join(' ')
          }
        >
          <Icon name={item.icon} />
          <span>{item.label}</span>
        </NavLink>
      ))}

      <button type="button" className="nx-bottom-nav__item" onClick={onOpenMore}>
        <Icon name="menu" />
        <span>Más</span>
      </button>
    </nav>
  )
}
