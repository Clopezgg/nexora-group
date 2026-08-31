import { Link } from 'react-router-dom'
import { Icon, type IconName } from '../../design-system'
import { formatMoney } from '../../utils/currency'
import type { DashboardSummary } from '../../types/dashboard'

interface MiTrabajoHoyProps {
  summary: DashboardSummary
}

interface WorkTile {
  label: string
  icon: IconName
  to: string
  hint?: string
  count?: number
  tone: 'neutral' | 'warning' | 'danger'
}

/** "Mi trabajo hoy" (§18) — tarjetas compactas, todas clicables, hacia el
 * trabajo pendiente real del usuario. Sin tarjetas decorativas. */
export function MiTrabajoHoy({ summary }: MiTrabajoHoyProps) {
  const currency = summary.currency || 'HNL'
  const pendingApprovals = summary.pendingApprovals ?? 0
  const overduePayables = summary.overduePayables ?? 0
  const tiles: WorkTile[] = [
    {
      label: 'Aprobaciones',
      icon: 'inbox',
      to: '/inicio/aprobaciones',
      count: pendingApprovals,
      tone: pendingApprovals > 0 ? 'warning' : 'neutral',
    },
    {
      label: 'Por pagar vencidas',
      icon: 'card',
      to: '/finanzas/cuentas-por-pagar',
      count: overduePayables,
      hint: formatMoney(summary.overduePayablesAmount ?? 0, currency),
      tone: overduePayables > 0 ? 'danger' : 'neutral',
    },
    {
      label: 'Por cobrar',
      icon: 'receipt',
      to: '/finanzas/cuentas-por-cobrar',
      hint: formatMoney(summary.receivablesOutstanding ?? 0, currency),
      tone: 'neutral',
    },
    {
      label: 'Excepciones',
      icon: 'warning',
      to: '/finanzas/excepciones',
      hint: 'Revisar centro de excepciones',
      tone: 'neutral',
    },
    {
      label: 'Conciliaciones',
      icon: 'shuffle',
      to: '/finanzas/conciliacion-subledger',
      hint: 'Subledger ↔ GL',
      tone: 'neutral',
    },
    {
      label: 'Evidencias',
      icon: 'camera',
      to: '/control/evidencias',
      hint: 'Documentos y soportes',
      tone: 'neutral',
    },
  ]

  return (
    <section className="nx-worktoday" aria-label="Mi trabajo hoy">
      <h2 className="nx-worktoday__title">Mi trabajo hoy</h2>
      <div className="nx-worktoday__grid">
        {tiles.map((tile) => (
          <Link key={tile.label} to={tile.to} className="nx-worktoday__tile">
            <span className="nx-worktoday__icon" aria-hidden="true">
              <Icon name={tile.icon} />
            </span>
            <span className="nx-worktoday__body">
              <span className="nx-worktoday__label">{tile.label}</span>
              {tile.hint ? <span className="nx-worktoday__hint">{tile.hint}</span> : null}
            </span>
            {typeof tile.count === 'number' ? (
              <span className={`nx-worktoday__count nx-worktoday__count--${tile.tone}`}>
                {tile.count}
              </span>
            ) : (
              <span className="nx-worktoday__chevron" aria-hidden="true">
                →
              </span>
            )}
          </Link>
        ))}
      </div>
    </section>
  )
}
