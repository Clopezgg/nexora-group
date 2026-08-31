import { useNavigate } from 'react-router-dom'
import { Sheet, Icon, type IconName } from '../design-system'
import { useAuth } from '../features/auth/auth-context'

interface QuickCreateProps {
  open: boolean
  onClose: () => void
}

interface QuickAction {
  label: string
  icon: IconName
  to: string
  requiredAny: string[]
}

/** Quick Create (§10) — sólo acciones reales y funcionales, filtradas por
 * permisos. Cada una navega a la pantalla del módulo correspondiente. */
const ACTIONS: QuickAction[] = [
  { label: 'Nuevo comprobante', icon: 'receipt', to: '/finanzas/comprobantes', requiredAny: ['treasury.voucher:read'] },
  { label: 'Registrar gasto', icon: 'card', to: '/finanzas/tesoreria', requiredAny: ['treasury.general_expense:create', 'treasury.account:read'] },
  { label: 'Registrar remesa', icon: 'bank', to: '/finanzas/tesoreria', requiredAny: ['treasury.remittance:create', 'treasury.account:read'] },
  { label: 'Nueva factura de proveedor', icon: 'file', to: '/finanzas/cuentas-por-pagar', requiredAny: ['ap.supplier_invoice:read'] },
  { label: 'Nuevo cobro', icon: 'receipt', to: '/comercial/cobros', requiredAny: ['ar.customer_receipt:read'] },
  { label: 'Nueva evidencia', icon: 'camera', to: '/control/evidencias', requiredAny: ['document.evidence:read'] },
  { label: 'Nuevo proyecto', icon: 'project', to: '/proyectos', requiredAny: ['project:read'] },
]

export function QuickCreate({ open, onClose }: QuickCreateProps) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const grants = new Set(user?.permissions ?? [])
  const actions = ACTIONS.filter((action) => action.requiredAny.some((permission) => grants.has(permission)))

  return (
    <Sheet open={open} title="Crear" onClose={onClose}>
      {actions.length === 0 ? (
        <p className="nx-field__hint">No tienes permisos para crear registros nuevos.</p>
      ) : (
        <ul className="nx-quick-create">
          {actions.map((action) => (
            <li key={action.label}>
              <button
                type="button"
                className="nx-quick-create__action"
                onClick={() => {
                  onClose()
                  navigate(action.to)
                }}
              >
                <span className="nx-quick-create__icon" aria-hidden="true">
                  <Icon name={action.icon} />
                </span>
                {action.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </Sheet>
  )
}
