import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { dashboardService } from '../../services/dashboardService'
import { ApiError } from '../../services/httpClient'
import { useAuth } from '../auth/auth-context'
import { resolveHomeConfig } from './roleHomes'
import { Card, ErrorState, LoadingState, StatCard } from '../../design-system'
import './HomePage.css'

const currencyFormatter = new Intl.NumberFormat('es-HN', {
  style: 'currency',
  currency: 'HNL',
  maximumFractionDigits: 0,
})

export function HomePage() {
  const { user } = useAuth()
  const config = resolveHomeConfig(user?.roles ?? [])

  const { data, error, isLoading, isError, refetch } = useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: dashboardService.getSummary,
    enabled: config.showTreasurySummary,
  })
  const sessionExpired = error instanceof ApiError && error.status === 401

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
            title={sessionExpired ? 'Tu sesión necesita renovarse' : 'No se pudo cargar el dashboard'}
            description={
              sessionExpired
                ? 'Cierra sesión y vuelve a ingresar para continuar.'
                : 'No fue posible comunicarse con el servidor. Intenta de nuevo.'
            }
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

      <section className="nx-home__sections" aria-label="Accesos principales">
        {config.sections.map((section) => (
          <Link key={section.title} className="nx-home__quick-link" to={section.path}>
            <Card title={section.title}>
              <p>{section.description}</p>
              <span className="nx-home__quick-action">Abrir módulo</span>
            </Card>
          </Link>
        ))}
      </section>
    </div>
  )
}
