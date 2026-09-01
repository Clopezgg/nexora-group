import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Badge,
  Card,
  CompanySelector,
  EmptyState,
  ErrorState,
  LoadingState,
  Modal,
  Select,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { cashForecastService } from '../../services/cashForecastService'
import {
  cashFlowActualService,
  type CashFlowGranularity,
  type CashFlowMovement,
  type CashFlowPeriod,
} from '../../services/cashFlowActualService'
import { formatMoney } from '../../utils/currency'
import './CashForecastPage.css'

type Mode = 'REALIZADO' | 'PROYECTADO'
type RangePreset = '1M' | '3M' | '6M' | '12M'

const RANGE_DAYS: Record<RangePreset, number> = { '1M': 30, '3M': 90, '6M': 182, '12M': 365 }

function isoDaysAgo(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().slice(0, 10)
}
const TODAY = new Date().toISOString().slice(0, 10)

export function CashForecastPage() {
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } =
    useActiveCompany()
  const [mode, setMode] = useState<Mode>('REALIZADO')
  const [range, setRange] = useState<RangePreset>('3M')
  const [granularity, setGranularity] = useState<CashFlowGranularity | 'auto'>('auto')
  const [drill, setDrill] = useState<{ from: string; to: string; label: string } | null>(null)

  const from = isoDaysAgo(RANGE_DAYS[range])

  const seriesQuery = useQuery({
    queryKey: ['cash-flow-series', activeCompanyId, from, granularity],
    queryFn: () =>
      cashFlowActualService.series({
        companyId: activeCompanyId as string,
        from,
        to: TODAY,
        granularity: granularity === 'auto' ? undefined : granularity,
      }),
    enabled: Boolean(activeCompanyId) && mode === 'REALIZADO',
  })
  const forecastQuery = useQuery({
    queryKey: ['cash-forecast', activeCompanyId],
    queryFn: () => cashForecastService.get(activeCompanyId as string),
    enabled: Boolean(activeCompanyId) && mode === 'PROYECTADO',
  })
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

  const currency =
    mode === 'REALIZADO' ? seriesQuery.data?.currencyCode : forecastQuery.data?.currencyCode
  const money = (v: number) => formatMoney(v, currency)

  const chartData: Array<{
    key: string
    Entradas: number
    Salidas: number
    Saldo: number
    _period: CashFlowPeriod | null
  }> = useMemo(() => {
    if (mode === 'REALIZADO') {
      return (seriesQuery.data?.periods ?? []).map((p: CashFlowPeriod) => ({
        key: p.label,
        Entradas: p.inflows,
        Salidas: -Math.abs(p.outflows),
        Saldo: p.closingBalance,
        _period: p as CashFlowPeriod | null,
      }))
    }
    return (forecastQuery.data?.weeks ?? []).map((w) => ({
      key: `S${w.weekIndex + 1}`,
      Entradas: w.inflows,
      Salidas: -Math.abs(w.outflows),
      Saldo: w.projectedBalance,
      _period: null as CashFlowPeriod | null,
    }))
  }, [mode, seriesQuery.data, forecastQuery.data])

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return <EmptyState icon="chart" title="Configura una compañía primero" description="El flujo de caja necesita una compañía." />
  }

  const query = mode === 'REALIZADO' ? seriesQuery : forecastQuery
  const series = seriesQuery.data
  const forecast = forecastQuery.data

  const periodColumns: TableColumn<CashFlowPeriod>[] = [
    { key: 'label', header: 'Período', render: (p) => p.label },
    { key: 'in', header: 'Entradas', render: (p) => money(p.inflows) },
    { key: 'out', header: 'Salidas', render: (p) => money(p.outflows) },
    { key: 'net', header: 'Neto', render: (p) => (
      <span style={{ color: p.net < 0 ? 'var(--nx-color-negative)' : 'var(--nx-color-positive)' }}>{money(p.net)}</span>
    ) },
    { key: 'bal', header: 'Saldo al cierre', render: (p) => (
      <span style={{ color: p.closingBalance < 0 ? 'var(--nx-color-negative)' : undefined, fontWeight: 600 }}>
        {money(p.closingBalance)}
      </span>
    ) },
    { key: 'mov', header: 'Mov.', render: (p) => (
      <button
        type="button"
        className="nx-linkbutton"
        onClick={() => setDrill({ from: p.periodStart, to: p.periodEnd, label: p.label })}
        disabled={p.movementCount === 0}
      >
        {p.movementCount}
      </button>
    ) },
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
        <span style={{ color: m.direction === 'OUTFLOW' ? 'var(--nx-color-negative)' : 'var(--nx-color-positive)', fontWeight: 600 }}>
          {m.direction === 'OUTFLOW' ? '−' : '+'}{money(m.amount)}
        </span>
      ),
    },
  ]

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

      <div className="nx-segmented" role="tablist" aria-label="Modo de flujo de caja">
        {(['REALIZADO', 'PROYECTADO'] as const).map((option) => (
          <button
            key={option}
            type="button"
            role="tab"
            aria-selected={mode === option}
            className={`nx-segmented__option${mode === option ? ' nx-segmented__option--active' : ''}`}
            onClick={() => setMode(option)}
          >
            {option === 'REALIZADO' ? 'Realizado' : 'Proyectado'}
          </button>
        ))}
      </div>

      {mode === 'REALIZADO' ? (
        <div className="nx-cashflow-controls">
          <div className="nx-segmented" role="group" aria-label="Rango">
            {(['1M', '3M', '6M', '12M'] as const).map((r) => (
              <button
                key={r}
                type="button"
                className={`nx-segmented__option${range === r ? ' nx-segmented__option--active' : ''}`}
                onClick={() => setRange(r)}
              >
                {r}
              </button>
            ))}
          </div>
          <Select
            label="Agrupar"
            value={granularity}
            onChange={(e) => setGranularity(e.target.value as CashFlowGranularity | 'auto')}
          >
            <option value="auto">Auto</option>
            <option value="day">Día</option>
            <option value="week">Semana</option>
            <option value="month">Mes</option>
          </Select>
        </div>
      ) : null}

      <Card>
        {query.isLoading ? (
          <LoadingState label={mode === 'REALIZADO' ? 'Cargando movimiento real…' : 'Proyectando…'} />
        ) : query.isError ? (
          <ErrorState description="No se pudo calcular el flujo de caja." onRetry={() => query.refetch()} />
        ) : chartData.length > 0 &&
          (mode === 'PROYECTADO' || chartData.some((d) => d.Entradas !== 0 || d.Salidas !== 0)) ? (
          <>
            <div className="nx-treasury__actions">
              {mode === 'REALIZADO' && series ? (
                <>
                  <Badge>Saldo inicial {money(series.openingBalance)}</Badge>
                  <Badge tone="success">Entradas {money(series.totalInflows)}</Badge>
                  <Badge tone="danger">Salidas {money(series.totalOutflows)}</Badge>
                  <Badge>Saldo al cierre {money(series.closingBalance)}</Badge>
                  <Badge tone="neutral">
                    {series.dateFrom} → {series.dateTo} · {series.granularity === 'day' ? 'diario' : series.granularity === 'week' ? 'semanal' : 'mensual'}
                  </Badge>
                </>
              ) : null}
              {mode === 'PROYECTADO' && forecast ? (
                <>
                  <Badge>Saldo inicial {money(forecast.openingBalance)}</Badge>
                  {forecast.hasLiquidityAlert ? (
                    <Badge tone="danger">
                      Alerta de liquidez · descubierto en la semana {(forecast.firstNegativeWeekIndex ?? 0) + 1} ·
                      mínimo {money(forecast.minProjectedBalance)}
                    </Badge>
                  ) : (
                    <Badge tone="success">Sin descubierto proyectado en el horizonte</Badge>
                  )}
                </>
              ) : null}
            </div>

            <div style={{ width: '100%', height: 300, marginTop: '0.75rem' }}>
              <ResponsiveContainer>
                <ComposedChart
                  data={chartData}
                  margin={{ top: 8, right: 16, left: 8, bottom: 0 }}
                  onClick={(state) => {
                    const payload = (state as { activePayload?: Array<{ payload?: { _period?: CashFlowPeriod | null } }> })
                      ?.activePayload?.[0]?.payload
                    const p = payload?._period
                    if (p) setDrill({ from: p.periodStart, to: p.periodEnd, label: p.label })
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--nx-chart-grid, #e6ecf3)" vertical={false} />
                  <XAxis dataKey="key" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                  <YAxis width={78} tick={{ fontSize: 11 }} tickFormatter={(v) => money(Number(v))} />
                  <Tooltip
                    formatter={(value) => money(Math.abs(Number(value)))}
                    labelFormatter={(label) => {
                      const p = chartData.find((d) => d.key === label)?._period
                      return p ? `${p.label} · ${p.movementCount} movimiento(s)` : String(label)
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <ReferenceLine y={0} stroke="var(--nx-color-border-strong, #b9c9dc)" />
                  <Bar dataKey="Entradas" fill="var(--nx-color-positive, #0f9f6e)" barSize={14} radius={[3, 3, 0, 0]} />
                  <Bar dataKey="Salidas" fill="var(--nx-color-negative, #dc3f50)" barSize={14} radius={[0, 0, 3, 3]} />
                  <Line type="monotone" dataKey="Saldo" stroke="var(--nx-color-accent, #1769d2)" strokeWidth={2} dot={{ r: 2 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            {mode === 'REALIZADO' && series ? (
              <>
                <p className="nx-field__hint">Toca una barra o una fila para ver los movimientos del período.</p>
                <Table
                  columns={periodColumns}
                  rows={series.periods}
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
