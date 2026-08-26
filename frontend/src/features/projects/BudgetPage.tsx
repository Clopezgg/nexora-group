import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, EmptyState, ErrorState, LoadingState, MoneyInput, StatCard } from '../../design-system'
import { projectService } from '../../services/projectService'
import { RequiresActiveProject } from './RequiresActiveProject'

const currencyFormatter = new Intl.NumberFormat('es-HN', { minimumFractionDigits: 2 })

function formatAmount(value: string | null): string {
  if (value === null) return '—'
  return currencyFormatter.format(Number(value))
}

function BudgetAndForecast({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient()
  const [baselineAmount, setBaselineAmount] = useState<number | null>(null)

  const summaryQuery = useQuery({
    queryKey: ['budget-summary', projectId],
    queryFn: () => projectService.getBudgetSummary(projectId),
  })
  const activeBudgetQuery = useQuery({
    queryKey: ['budget-active', projectId],
    queryFn: () => projectService.getActiveBudget(projectId),
    retry: false,
  })
  const forecastQuery = useQuery({
    queryKey: ['forecast', projectId],
    queryFn: () => projectService.getForecast(projectId),
  })

  const createBaseline = useMutation({
    mutationFn: () =>
      projectService.createBaseline(projectId, {
        currencyCode: 'HNL',
        lines: [{ authorizedAmount: baselineAmount ?? 0 }],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budget-summary', projectId] })
      queryClient.invalidateQueries({ queryKey: ['budget-active', projectId] })
      queryClient.invalidateQueries({ queryKey: ['forecast', projectId] })
    },
  })

  if (summaryQuery.isLoading || forecastQuery.isLoading) return <LoadingState label="Cargando presupuesto…" />
  if (summaryQuery.isError || forecastQuery.isError) {
    return <ErrorState description="No se pudo cargar el presupuesto." onRetry={() => summaryQuery.refetch()} />
  }

  const summary = summaryQuery.data
  const forecast = forecastQuery.data
  const showCreateBaseline = !activeBudgetQuery.isLoading && !activeBudgetQuery.data

  return (
    <div>
      {showCreateBaseline ? (
        <Card title="Crear presupuesto BASELINE">
          <p className="nx-field__label">
            El BASELINE se crea una sola vez y nunca se sobrescribe — cualquier cambio posterior se
            hace vía Órdenes de Cambio.
          </p>
          <MoneyInput label="Monto autorizado (HNL)" value={baselineAmount} onChange={setBaselineAmount} />
          <Button
            disabled={baselineAmount === null || createBaseline.isPending}
            loading={createBaseline.isPending}
            onClick={() => createBaseline.mutate()}
          >
            Crear BASELINE
          </Button>
        </Card>
      ) : null}

      {summary ? (
        <div className="nx-home__grid">
          <StatCard label="Autorizado" value={formatAmount(summary.authorized)} />
          <StatCard label="Comprometido" value={formatAmount(summary.committed)} />
          <StatCard label="Devengado" value={formatAmount(summary.accrued)} />
          <StatCard label="Pagado" value={formatAmount(summary.paid)} />
          <StatCard label="Disponible" value={formatAmount(summary.available)} />
        </div>
      ) : null}

      {forecast ? (
        <Card title="Forecast (Earned Value)">
          <div className="nx-home__grid">
            <StatCard label="BAC" value={formatAmount(forecast.bac)} />
            <StatCard label="PV" value={formatAmount(forecast.pv)} />
            <StatCard label="EV" value={formatAmount(forecast.ev)} />
            <StatCard label="AC" value={formatAmount(forecast.ac)} />
            <StatCard label="CPI" value={forecast.cpi ?? '—'} />
            <StatCard label="SPI" value={forecast.spi ?? '—'} />
            <StatCard label="ETC" value={formatAmount(forecast.etc)} />
            <StatCard label="EAC" value={formatAmount(forecast.eac)} />
            <StatCard label="VAC" value={formatAmount(forecast.vac)} />
          </div>
          {forecast.pv === null ? (
            <EmptyState
              icon="📈"
              title="Forecast incompleto"
              description="Registra un avance de proyecto en Avances para calcular PV/EV/CPI/SPI."
            />
          ) : null}
        </Card>
      ) : null}
    </div>
  )
}

export function BudgetPage() {
  return (
    <div>
      <h1 className="nx-dashboard__title">Presupuestos</h1>
      <RequiresActiveProject>{(projectId) => <BudgetAndForecast projectId={projectId} />}</RequiresActiveProject>
    </div>
  )
}
