import { lazy, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { dashboardService } from '../../services/dashboardService'
import { formatMoney } from '../../utils/currency'
import { ApiError } from '../../services/httpClient'
import { useAuth } from '../auth/auth-context'
import { resolveHomeConfig } from './roleHomes'
import { Card, ErrorState, LoadingState, StatCard } from '../../design-system'
import './HomePage.css'

const FinancialCharts = lazy(() => import('./FinancialCharts'))

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
    <div className="nx-home">
      <header className="nx-home__header">
        <div>
          <p className="nx-home__eyebrow">Resumen ejecutivo</p>
          <h1 className="nx-dashboard__title">{config.title}</h1>
          <p className="nx-home__subtitle">{config.subtitle}</p>
        </div>
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
          <>
            <section className="nx-home__grid" aria-label="Indicadores financieros">
              <StatCard label="Saldo disponible de Tesorería" value={formatMoney(data.treasuryBalance, data.currency)} />
              <StatCard label="Ingresos del período" value={formatMoney(data.periodIncome, data.currency)} />
              <StatCard label="Gastos del período" value={formatMoney(data.periodExpense, data.currency)} />
              <StatCard label="Proyectos activos" value={data.activeProjects} />
            </section>

            <Suspense fallback={<LoadingState label="Preparando gráficos…" />}>
              <FinancialCharts
                cashFlow={data.cashFlow ?? []}
                expensesByScope={data.expensesByScope ?? []}
                currency={data.currency}
              />
            </Suspense>

            <section className="nx-home__operations" aria-label="Información operativa">
              <StatCard label="Aprobaciones pendientes" value={data.pendingApprovals} />
              <StatCard
                label="Cuentas por pagar vencidas"
                value={formatMoney(data.overduePayablesAmount, data.currency)}
                delta={{ value: `${data.overduePayables} documento(s)`, tone: data.overduePayables > 0 ? 'negative' : 'neutral' }}
              />
              <StatCard label="Cuentas por cobrar" value={formatMoney(data.receivablesOutstanding, data.currency)} />
            </section>
          </>
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
