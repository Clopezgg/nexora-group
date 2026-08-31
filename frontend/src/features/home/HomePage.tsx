import { lazy, Suspense } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { dashboardService } from '../../services/dashboardService'
import { projectService } from '../../services/projectService'
import { formatMoney } from '../../utils/currency'
import { ApiError } from '../../services/httpClient'
import { useAuth } from '../auth/auth-context'
import { useActiveContext } from '../context/useActiveContext'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { resolveHomeConfig } from './roleHomes'
import { MiTrabajoHoy } from './MiTrabajoHoy'
import { Card, EmptyState, ErrorState, LoadingState, StatCard } from '../../design-system'
import './HomePage.css'

const FinancialCharts = lazy(() => import('./FinancialCharts'))

function money(value: string | null, currency: string) {
  return value === null ? '—' : formatMoney(Number(value), currency)
}

function percent(value: string | null) {
  return value === null ? '—' : `${Number(value).toFixed(1)}%`
}

export function HomePage() {
  const { user } = useAuth()
  const { activeCompany, activeCompanyId } = useActiveCompany()
  const { context } = useActiveContext()
  const config = resolveHomeConfig(user?.roles ?? [])

  const companySummaryQuery = useQuery({
    queryKey: ['dashboard', 'summary', activeCompanyId],
    queryFn: () => dashboardService.getSummary(activeCompanyId),
    enabled: config.showTreasurySummary && Boolean(activeCompanyId) && !context.activeProjectId,
  })
  const projectQuery = useQuery({
    queryKey: ['project', context.activeProjectId],
    queryFn: () => projectService.get(context.activeProjectId as string),
    enabled: Boolean(context.activeProjectId),
  })
  const projectSummaryQuery = useQuery({
    queryKey: ['project', context.activeProjectId, 'financial-summary'],
    queryFn: () => projectService.getFinancialSummary(context.activeProjectId as string),
    enabled: Boolean(context.activeProjectId),
  })

  const error = companySummaryQuery.error
  const sessionExpired = error instanceof ApiError && error.status === 401

  if (context.activeProjectId) {
    if (projectQuery.isLoading || projectSummaryQuery.isLoading) return <LoadingState label="Cargando resumen del proyecto…" />
    if (projectQuery.isError || projectSummaryQuery.isError || !projectQuery.data || !projectSummaryQuery.data) {
      return <ErrorState description="No se pudo cargar el resumen del proyecto seleccionado." onRetry={() => { projectQuery.refetch(); projectSummaryQuery.refetch() }} />
    }
    const project = projectQuery.data
    const summary = projectSummaryQuery.data
    const currency = summary.currencyCode
    return (
      <div className="nx-home">
        <header className="nx-home__header">
          <div>
            <p className="nx-home__eyebrow">Vista de proyecto</p>
            <h1 className="nx-dashboard__title">Proyecto: {project.name}</h1>
            <p className="nx-home__subtitle">Métricas exclusivas de este proyecto; no se mezclan con la vista financiera de la empresa.</p>
          </div>
        </header>

        <section className="nx-home__grid" aria-label="Resumen comercial del proyecto">
          <StatCard label="Valor contractual" value={money(summary.contractValue, currency)} />
          <StatCard label="Presupuesto de costos" value={money(summary.currentBudget, currency)} />
          <StatCard label="Costo real" value={money(summary.actualCost, currency)} />
          <StatCard label="Avance físico" value={percent(summary.progressPercent)} />
        </section>
        <section className="nx-home__grid" aria-label="Rentabilidad del proyecto">
          <StatCard label="Utilidad esperada" value={money(summary.expectedProfit, currency)} />
          <StatCard label="Margen esperado" value={percent(summary.expectedMarginPercent)} />
          <StatCard label="Facturado" value={money(summary.invoiced, currency)} />
          <StatCard label="Cobrado" value={money(summary.collected, currency)} />
        </section>
        <section className="nx-home__grid" aria-label="Control de costos del proyecto">
          <StatCard label="Comprometido" value={money(summary.committed, currency)} />
          <StatCard label="Devengado" value={money(summary.accrued, currency)} />
          <StatCard label="Pagado" value={money(summary.paid, currency)} />
          <StatCard label="Disponible de presupuesto" value={money(summary.available, currency)} />
        </section>
        <Card title="Detalle del proyecto">
          <p>El valor contractual proviene de Comercial/Contratos; el presupuesto es exclusivamente presupuesto de costos.</p>
          <Link to={`/proyectos/${project.id}`}>Abrir cockpit financiero completo</Link>
        </Card>
      </div>
    )
  }

  return (
    <div className="nx-home">
      <header className="nx-home__header">
        <div>
          <p className="nx-home__eyebrow">Vista empresa</p>
          <h1 className="nx-dashboard__title">{config.title}</h1>
          <p className="nx-home__subtitle">{activeCompany?.name ?? config.subtitle} · Tesorería y operación consolidada de la empresa.</p>
        </div>
      </header>

      {!activeCompanyId ? (
        <EmptyState title="Sin empresa activa" description="Selecciona o configura una compañía para cargar el dashboard." />
      ) : config.showTreasurySummary ? (
        companySummaryQuery.isLoading ? (
          <LoadingState label="Cargando indicadores…" />
        ) : companySummaryQuery.isError || !companySummaryQuery.data ? (
          <ErrorState
            title={sessionExpired ? 'Tu sesión necesita renovarse' : 'No se pudo cargar el dashboard'}
            description={sessionExpired ? 'Cierra sesión y vuelve a ingresar para continuar.' : 'No fue posible cargar los indicadores de la empresa.'}
            onRetry={() => companySummaryQuery.refetch()}
          />
        ) : (
          <>
            <section className="nx-home__grid nx-home__grid--kpi" aria-label="Indicadores financieros">
              <StatCard label="Tesorería · disponible" value={formatMoney(companySummaryQuery.data.treasuryBalance, companySummaryQuery.data.currency)} />
              <StatCard
                label={companySummaryQuery.data.fiscalPeriodLabel ? `Ingresos · ${companySummaryQuery.data.fiscalPeriodLabel}` : 'Ingresos del mes calendario'}
                value={formatMoney(companySummaryQuery.data.periodIncome, companySummaryQuery.data.currency)}
              />
              <StatCard
                label={companySummaryQuery.data.fiscalPeriodLabel ? `Gastos · ${companySummaryQuery.data.fiscalPeriodLabel}` : 'Gastos del mes calendario'}
                value={formatMoney(companySummaryQuery.data.periodExpense, companySummaryQuery.data.currency)}
              />
              <StatCard label="Proyectos en ejecución" value={companySummaryQuery.data.activeProjects} />
            </section>

            {!companySummaryQuery.data.fiscalPeriodLabel ? (
              <Card title="Período fiscal no configurado">
                <p>Mientras no exista un período fiscal actual, Ingresos y Gastos se muestran como mes calendario y se etiquetan explícitamente así.</p>
                <Link to="/control/configuracion">Configurar períodos fiscales</Link>
              </Card>
            ) : null}

            <Suspense fallback={<LoadingState label="Preparando gráficos…" />}>
              <FinancialCharts
                cashFlow={companySummaryQuery.data.cashFlow ?? []}
                expensesByScope={companySummaryQuery.data.expensesByScope ?? []}
                currency={companySummaryQuery.data.currency}
              />
            </Suspense>

            <MiTrabajoHoy summary={companySummaryQuery.data} />
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
