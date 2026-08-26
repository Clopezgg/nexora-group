import { EmptyState } from '../design-system'

interface PlaceholderPageProps {
  title: string
  description?: string
}

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <div>
      <h1 className="nx-dashboard__title">{title}</h1>
      <EmptyState
        icon="🚧"
        title="Módulo en construcción"
        description={
          description ??
          'Esta sección de Nexora Group todavía no está implementada. Llegará en una fase posterior del roadmap.'
        }
      />
    </div>
  )
}
