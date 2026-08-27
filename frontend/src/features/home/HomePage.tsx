import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Cell, Legend, Line, LineChart, Pie, PieChart, Tooltip, XAxis, YAxis } from 'recharts'
import { dashboardService } from '../../services/dashboardService'
import { formatMoney } from '../../utils/currency'
import { ApiError } from '../../services/httpClient'
import { useAuth } from '../auth/auth-context'
import { resolveHomeConfig } from './roleHomes'
import { Card, ChartCard, ErrorState, LoadingState, StatCard } from '../../design-system'
import './HomePage.css'

const scopeLabels: Record<string, string> = {
  CENTRAL: 'Central',
  GENERAL: 'General',
  PROJECT: 'Proyecto',
}
const scopeColors: Record<string, string> = {
  CENTRAL: '#2563eb',
  GENERAL: '#0f766e',
  PROJECT: '#7c3aed',
}

export function HomePage() {
  const { user } = useAuth()
  const config = resolveHomeConfig(user?.roles ?? [])

  const { data, error, isLoading, isError, refetch } = useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: dashboardService.getSummary,
    enabled: config.showTreasurySummary,
  })
  const sessionExpired = error instanceof ApiError && error.status === 401
  const cashFlow = data?.cashFlow ?? []
  const scopeData = (data?.expensesByScope ?? []).map((item) => ({
    ...item,
    label: scopeLabels[item.scope] ?? item.scope,
  }))
  const hasCashFlow = cashFlow.some((item) => item.income !== 0 || item.expense !== 0)

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

            <section className="nx-home__charts" aria-label="Visualizaciones financieras">
              <ChartCard title="Ingresos vs. gastos" subtitle="Últimos seis meses" hasData={hasCashFlow}>
                <LineChart data={cashFlow} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
                  <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} width={72} />
                  <Tooltip formatter={(value) => formatMoney(Number(value), data.currency)} />
                  <Legend />
                  <Line type="monotone" dataKey="income" name="Ingresos" stroke="#0f9f6e" strokeWidth={2.5} dot={false} />
                  <Line type="monotone" dataKey="expense" name="Gastos" stroke="#dc3f50" strokeWidth={2.5} dot={false} />
                </LineChart>
              </ChartCard>
              <ChartCard title="Gastos por alcance" subtitle="Período actual" hasData={scopeData.length > 0}>
                <PieChart>
                  <Pie data={scopeData} dataKey="amount" nameKey="label" innerRadius={54} outerRadius={86} paddingAngle={2}>
                    {scopeData.map((item) => (
                      <Cell key={item.scope} fill={scopeColors[item.scope] ?? '#64748b'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatMoney(Number(value), data.currency)} />
                  <Legend />
                </PieChart>
              </ChartCard>
            </section>

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
