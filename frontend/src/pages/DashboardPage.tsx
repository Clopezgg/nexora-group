import { useQuery } from '@tanstack/react-query'
import { dashboardService } from '../services/dashboardService'
import { Card, ErrorState, LoadingState } from '../design-system'
import './DashboardPage.css'

const currencyFormatter = new Intl.NumberFormat('es-MX', {
  style: 'currency',
  currency: 'MXN',
  maximumFractionDigits: 0,
})

export function DashboardPage() {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: dashboardService.getSummary,
  })

  if (isLoading) {
    return <LoadingState label="Cargando dashboard…" />
  }

  if (isError || !data) {
    return (
      <ErrorState
        title="No se pudo cargar el dashboard"
        description="Verifica tu conexión con el servidor e intenta de nuevo."
        onRetry={() => refetch()}
      />
    )
  }

  return (
    <div>
      <h1 className="nx-dashboard__title">Dashboard</h1>
      <div className="nx-dashboard__grid">
        <Card title="Saldo Tesorería" value={currencyFormatter.format(data.treasuryBalance)} />
        <Card title="Ingresos del periodo" value={currencyFormatter.format(data.periodIncome)} />
        <Card title="Gastos del periodo" value={currencyFormatter.format(data.periodExpense)} />
        <Card title="Proyectos activos" value={data.activeProjects} />
      </div>
    </div>
  )
}
