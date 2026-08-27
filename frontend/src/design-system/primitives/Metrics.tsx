import type { ReactElement, ReactNode } from 'react'
import { ResponsiveContainer } from 'recharts'
import { EmptyState } from './States'

interface StatCardProps {
  label: string
  value: ReactNode
  delta?: { value: string; tone: 'positive' | 'negative' | 'neutral' }
  icon?: ReactNode
}

export function StatCard({ label, value, delta, icon }: StatCardProps) {
  return (
    <div className="nx-stat-card">
      <div className="nx-stat-card__head">
        <span className="nx-stat-card__label">{label}</span>
        {icon ? (
          <span className="nx-stat-card__icon" aria-hidden="true">
            {icon}
          </span>
        ) : null}
      </div>
      <p className="nx-stat-card__value">{value}</p>
      {delta ? (
        <span className={`nx-stat-card__delta nx-stat-card__delta--${delta.tone}`}>
          {delta.value}
        </span>
      ) : null}
    </div>
  )
}

export function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="nx-metric">
      <span className="nx-metric__label">{label}</span>
      <span className="nx-metric__value">{value}</span>
    </div>
  )
}

interface ChartCardProps {
  title: string
  subtitle?: string
  height?: number
  hasData: boolean
  emptyMessage?: string
  children: ReactElement
}

/** Wraps a Recharts chart in a titled card with a real ResponsiveContainer — never renders fabricated series when `hasData` is false. */
export function ChartCard({
  title,
  subtitle,
  height = 260,
  hasData,
  emptyMessage = 'Aún no hay datos suficientes para graficar.',
  children,
}: ChartCardProps) {
  return (
    <div className="nx-chart-card">
      <div className="nx-chart-card__head">
        <p className="nx-chart-card__title">{title}</p>
        {subtitle ? <p className="nx-chart-card__subtitle">{subtitle}</p> : null}
      </div>
      {hasData ? (
        <div style={{ width: '100%', height }}>
          <ResponsiveContainer width="100%" height="100%">
            {children}
          </ResponsiveContainer>
        </div>
      ) : (
        <EmptyState icon="chart" title={emptyMessage} />
      )}
    </div>
  )
}
