import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  MoneyInput,
  StatCard,
  Table,
  type TableColumn,
} from '../../design-system'
import { projectService } from '../../services/projectService'
import { formatMoney } from '../../utils/currency'
import { RequiresActiveProject } from './RequiresActiveProject'

function formatAmount(value: string | null, currencyCode = 'HNL'): string {
  if (value === null) return '—'
  return formatMoney(Number(value), currencyCode)
}

interface BudgetBreakdownRow {
  key: string
  wbs: string
  authorized: number
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
  const wbsQuery = useQuery({
    queryKey: ['wbs', projectId],
    queryFn: () => projectService.listWbs(projectId),
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
  const activeBudget = activeBudgetQuery.data
  const showCreateBaseline = !activeBudgetQuery.isLoading && !activeBudget
  const currencyCode = activeBudget?.currencyCode ?? 'HNL'
  const authorized = Number(summary?.authorized ?? 0)
  const accrued = Number(summary?.accrued ?? 0)
  const executedPercent = authorized > 0 ? `${((accrued / authorized) * 100).toFixed(1)}%` : '—'
  const wbsNodes = Array.isArray(wbsQuery.data) ? wbsQuery.data : []
  const wbsById = new Map(wbsNodes.map((node) => [node.id, `${node.code} — ${node.name}`]))
  const authorizedByWbs = new Map<string, BudgetBreakdownRow>()

  for (const line of activeBudget?.lines ?? []) {
    const key = line.wbsNodeId ?? 'unassigned'
    const current = authorizedByWbs.get(key)
    authorizedByWbs.set(key, {
      key,
      wbs: line.wbsNodeId ? (wbsById.get(line.wbsNodeId) ?? 'WBS no disponible') : 'Sin WBS asignado',
      authorized: (current?.authorized ?? 0) + Number(line.authorizedAmount),
    })
  }

  const breakdownRows = [...authorizedByWbs.values()]
  const breakdownColumns: TableColumn<BudgetBreakdownRow>[] = [
    { key: 'wbs', header: 'WBS', render: (row) => row.wbs },
    {
      key: 'authorized',
      header: 'Autorizado',
      render: (row) => formatMoney(row.authorized, currencyCode),
    },
  ]

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
          <StatCard label="Autorizado" value={formatAmount(summary.authorized, currencyCode)} />
          <StatCard label="Comprometido" value={formatAmount(summary.committed, currencyCode)} />
          <StatCard label="Devengado" value={formatAmount(summary.accrued, currencyCode)} />
          <StatCard label="Pagado" value={formatAmount(summary.paid, currencyCode)} />
          <StatCard label="Disponible" value={formatAmount(summary.available, currencyCode)} />
          <StatCard label="Ejecutado" value={executedPercent} />
        </div>
      ) : null}

      {activeBudget ? (
        <Card title="Detalle autorizado por WBS">
          {wbsQuery.isLoading ? (
            <LoadingState label="Cargando detalle WBS…" />
          ) : wbsQuery.isError ? (
            <ErrorState description="No se pudo cargar el detalle WBS." onRetry={() => wbsQuery.refetch()} />
          ) : (
            <Table
              columns={breakdownColumns}
              rows={breakdownRows}
              getRowKey={(row) => row.key}
              emptyMessage="El presupuesto activo todavía no tiene líneas autorizadas."
            />
          )}
        </Card>
      ) : null}

      {forecast ? (
        <Card title="Forecast (Earned Value)">
          <div className="nx-home__grid">
            <StatCard label="BAC" value={formatAmount(forecast.bac, currencyCode)} />
            <StatCard label="PV" value={formatAmount(forecast.pv, currencyCode)} />
            <StatCard label="EV" value={formatAmount(forecast.ev, currencyCode)} />
            <StatCard label="AC" value={formatAmount(forecast.ac, currencyCode)} />
            <StatCard label="CPI" value={forecast.cpi ?? '—'} />
            <StatCard label="SPI" value={forecast.spi ?? '—'} />
            <StatCard label="ETC" value={formatAmount(forecast.etc, currencyCode)} />
            <StatCard label="EAC" value={formatAmount(forecast.eac, currencyCode)} />
            <StatCard label="VAC" value={formatAmount(forecast.vac, currencyCode)} />
          </div>
          {forecast.pv === null ? (
            <EmptyState
              icon="chart"
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
