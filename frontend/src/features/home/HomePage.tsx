import { useQuery } from '@tanstack/react-query'
import { dashboardService } from '../../services/dashboardService'
import { useAuth } from '../auth/auth-context'
import { resolveHomeConfig } from './roleHomes'
import { EmptyState, ErrorState, LoadingState, StatCard } from '../../design-system'
import './HomePage.css'

const currencyFormatter = new Intl.NumberFormat('es-MX', {
  style: 'currency',
  currency: 'MXN',
  maximumFractionDigits: 0,
})

export function HomePage() {
  const { user } = useAuth()
  const config = resolveHomeConfig(user?.roles ?? [])

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: dashboardService.getSummary,
    enabled: config.showTreasurySummary,
  })

  return (
    <div>
      <header className="nx-home__header">
        <h1 className="nx-dashboard__title">{config.title}</h1>
        <p className="nx-home__subtitle">{config.subtitle}</p>
      </header>

      {config.showTreasurySummary ? (
        isLoading ? (
          <LoadingState label="Cargando indicadores…" />
        ) : isError || !data ? (
          <ErrorState
            title="No se pudo cargar el dashboard"
            description="Verifica tu conexión con el servidor e intenta de nuevo."
            onRetry={() => refetch()}
          />
        ) : (
          <div className="nx-home__grid">
            <StatCard label="Saldo Tesorería" value={currencyFormatter.format(data.treasuryBalance)} />
            <StatCard label="Ingresos del periodo" value={currencyFormatter.format(data.periodIncome)} />
            <StatCard label="Gastos del periodo" value={currencyFormatter.format(data.periodExpense)} />
            <StatCard label="Proyectos activos" value={data.activeProjects} />
          </div>
        )
      ) : null}

      <div className="nx-home__sections">
        {config.sections.map((section) => (
          <div key={section.title} className="nx-home__section">
            <h2 className="nx-home__section-title">{section.title}</h2>
            <EmptyState title="Aún no disponible" description={section.description} />
          </div>
        ))}
      </div>
    </div>
  )
}
