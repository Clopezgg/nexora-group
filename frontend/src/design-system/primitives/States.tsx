import type { ReactNode } from 'react'
import { Icon } from './Icon'

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
}

export function EmptyState({ icon = <Icon name="clipboard" />, title, description }: EmptyStateProps) {
  return (
    <div className="nx-state" role="status">
      <span className="nx-state__icon" aria-hidden="true">
        {icon}
      </span>
      <p className="nx-state__title">{title}</p>
      {description ? <p className="nx-state__description">{description}</p> : null}
    </div>
  )
}

export function LoadingState({ label = 'Cargando…' }: { label?: string }) {
  return (
    <div className="nx-state" role="status" aria-live="polite">
      <span className="nx-state__spinner" aria-hidden="true" />
      <p className="nx-state__title">{label}</p>
    </div>
  )
}

interface ErrorStateProps {
  title?: string
  description?: string
  onRetry?: () => void
}

export function ErrorState({
  title = 'Ocurrió un error',
  description,
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="nx-state nx-state--error" role="alert">
      <span className="nx-state__icon" aria-hidden="true">
        <Icon name="warning" />
      </span>
      <p className="nx-state__title">{title}</p>
      {description ? <p className="nx-state__description">{description}</p> : null}
      {onRetry ? (
        <button className="nx-button nx-button--secondary" onClick={onRetry}>
          <span className="nx-button__label">Reintentar</span>
        </button>
      ) : null}
    </div>
  )
}
