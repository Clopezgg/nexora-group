import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Card,
  CompanySelector,
  EmptyState,
  ErrorState,
  LoadingState,
  Modal,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import {
  cashFlowActualService,
  type CashFlowMovement,
  type CashFlowPeriod,
} from '../../services/cashFlowActualService'
import { formatMoney } from '../../utils/currency'
import {
  CashFlowChart,
  CashFlowControls,
  CashFlowSummary,
  useCashFlowSeries,
  type CashFlowGranularityOption,
  type CashFlowMode,
  type CashFlowRange,
  type CashFlowRow,
} from './cashflow'
import './cashflow/cashflow.css'

export function CashForecastPage() {
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } =
    useActiveCompany()
  const [mode, setMode] = useState<CashFlowMode>('REALIZADO')
  const [range, setRange] = useState<CashFlowRange>('3M')
  const [granularity, setGranularity] = useState<CashFlowGranularityOption>('auto')
  const [drill, setDrill] = useState<{ from: string; to: string; label: string } | null>(null)

  const { rows, summary, hasMovement, isLoading: seriesLoading, isError: seriesError, refetch: seriesRefetch } =
    useCashFlowSeries({ companyId: activeCompanyId, mode, range, granularity })

  const drillQuery = useQuery({
    queryKey: ['cash-flow-movements', activeCompanyId, drill?.from, drill?.to],
    queryFn: () =>
      cashFlowActualService.movements({
        companyId: activeCompanyId as string,
        from: drill!.from,
        to: drill!.to,
      }),
    enabled: Boolean(activeCompanyId && drill),
  })

  const currency = summary?.currencyCode ?? 'HNL'
  const money = (v: number) => formatMoney(v, currency)

  const openDrill = (row: CashFlowRow) => {
    if (row.period) {
      setDrill({ from: row.period.periodStart, to: row.period.periodEnd, label: row.period.label })
    }
  }

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError)
    return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return (
      <EmptyState
        icon="chart"
        title="Configura una compañía primero"
        description="El flujo de caja necesita una compañía."
      />
    )
  }

  const periodColumns: TableColumn<CashFlowPeriod>[] = [
    { key: 'label', header: 'Período', render: (p) => p.label },
    { key: 'in', header: 'Entradas', render: (p) => money(p.inflows) },
    { key: 'out', header: 'Salidas', render: (p) => money(p.outflows) },
    {
      key: 'net',
      header: 'Neto',
      render: (p) => (
        <span style={{ color: p.net < 0 ? 'var(--nx-color-negative)' : 'var(--nx-color-positive)' }}>
          {money(p.net)}
        </span>
      ),
    },
    {
      key: 'bal',
      header: 'Saldo al cierre',
      render: (p) => (
        <span style={{ color: p.closingBalance < 0 ? 'var(--nx-color-negative)' : undefined, fontWeight: 600 }}>
          {money(p.closingBalance)}
        </span>
      ),
    },
    {
      key: 'mov',
      header: 'Mov.',
      render: (p) => (
        <button
          type="button"
          className="nx-linkbutton"
          onClick={() => setDrill({ from: p.periodStart, to: p.periodEnd, label: p.label })}
          disabled={p.movementCount === 0}
        >
          {p.movementCount}
        </button>
      ),
    },
  ]

  const movementColumns: TableColumn<CashFlowMovement>[] = [
    { key: 'date', header: 'Fecha', render: (m) => m.effectiveDate },
    { key: 'doc', header: 'Documento', render: (m) => m.documentNumber },
    { key: 'cat', header: 'Categoría', render: (m) => m.category },
    { key: 'concept', header: 'Concepto', render: (m) => m.concept ?? m.counterparty ?? '—' },
    {
      key: 'amount',
      header: 'Importe',
      render: (m) => (
        <span
          style={{
            color: m.direction === 'OUTFLOW' ? 'var(--nx-color-negative)' : 'var(--nx-color-positive)',
            fontWeight: 600,
          }}
        >
          {m.direction === 'OUTFLOW' ? '−' : '+'}
          {money(m.amount)}
        </span>
      ),
    },
  ]

  const periodRows = mode === 'REALIZADO' ? rows.map((r) => r.period).filter((p): p is CashFlowPeriod => Boolean(p)) : []

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <p className="nx-page__eyebrow">Tesorería</p>
          <h1 className="nx-dashboard__title">Flujo de caja</h1>
          <p className="nx-field__hint">
            {mode === 'REALIZADO'
              ? 'Movimiento REAL de las cuentas de tesorería, agrupado por fecha económica de cada transacción. Un aporte de capital o un financiamiento es entrada de caja pero no es ingreso contable.'
              : 'Posición de caja actual + cobros esperados (AR abierto) − pagos comprometidos (AP abierto). Solo compromisos ya registrados.'}
          </p>
        </div>
        <CompanySelector
          options={companies.map((company) => ({ id: company.id, label: company.name }))}
          value={activeCompanyId}
          onChange={setActiveCompanyId}
        />
      </header>

      <CashFlowControls
        mode={mode}
        onModeChange={setMode}
        range={range}
        onRangeChange={setRange}
        granularity={granularity}
        onGranularityChange={setGranularity}
      />

      <Card>
        {seriesLoading ? (
          <LoadingState label={mode === 'REALIZADO' ? 'Cargando movimiento real…' : 'Proyectando…'} />
        ) : seriesError ? (
          <ErrorState description="No se pudo calcular el flujo de caja." onRetry={seriesRefetch} />
        ) : hasMovement ? (
          <>
            {summary ? <CashFlowSummary summary={summary} /> : null}
            <CashFlowChart rows={rows} currency={currency} height={300} onSelectPeriod={openDrill} />
            {mode === 'REALIZADO' && periodRows.length > 0 ? (
              <>
                <p className="nx-field__hint">Toca una barra o una fila para ver los movimientos del período.</p>
                <Table
                  columns={periodColumns}
                  rows={periodRows}
                  getRowKey={(p) => String(p.index)}
                  emptyMessage="Sin períodos."
                />
              </>
            ) : null}
          </>
        ) : (
          <EmptyState
            icon="chart"
            title={
              mode === 'REALIZADO'
                ? 'Sin movimientos de tesorería en el rango seleccionado'
                : 'Sin compromisos AP/AR para proyectar'
            }
          />
        )}
      </Card>

      {drill ? (
        <Modal open title={`Movimientos · ${drill.label}`} onClose={() => setDrill(null)}>
          {drillQuery.isLoading ? (
            <LoadingState label="Cargando movimientos…" />
          ) : drillQuery.isError ? (
            <ErrorState description="No se pudieron cargar los movimientos." onRetry={() => drillQuery.refetch()} />
          ) : (
            <Table
              columns={movementColumns}
              rows={drillQuery.data ?? []}
              getRowKey={(m) => m.documentId}
              emptyMessage="Sin movimientos en este período."
            />
          )}
        </Modal>
      ) : null}
    </div>
  )
}
