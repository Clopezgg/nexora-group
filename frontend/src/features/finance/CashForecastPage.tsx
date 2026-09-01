import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  Badge,
  Card,
  CompanySelector,
  EmptyState,
  ErrorState,
  LoadingState,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { cashForecastService } from '../../services/cashForecastService'
import { cashFlowActualService } from '../../services/cashFlowActualService'
import { formatMoney } from '../../utils/currency'

type Mode = 'REALIZADO' | 'PROYECTADO'

interface WeekRow {
  weekIndex: number
  weekStart: string
  weekEnd: string
  inflows: number
  outflows: number
  net: number
  balance: number
}

export function CashForecastPage() {
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } =
    useActiveCompany()
  const [mode, setMode] = useState<Mode>('REALIZADO')

  const actualQuery = useQuery({
    queryKey: ['cash-flow-actual', activeCompanyId],
    queryFn: () => cashFlowActualService.get(activeCompanyId as string),
    enabled: Boolean(activeCompanyId) && mode === 'REALIZADO',
  })
  const forecastQuery = useQuery({
    queryKey: ['cash-forecast', activeCompanyId],
    queryFn: () => cashForecastService.get(activeCompanyId as string),
    enabled: Boolean(activeCompanyId) && mode === 'PROYECTADO',
  })

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return <EmptyState icon="chart" title="Configura una compañía primero" description="El flujo de caja necesita una compañía." />
  }

  const query = mode === 'REALIZADO' ? actualQuery : forecastQuery
  const currency =
    mode === 'REALIZADO' ? actualQuery.data?.currencyCode : forecastQuery.data?.currencyCode
  const money = (v: number) => formatMoney(v, currency)

  const rows: WeekRow[] =
    mode === 'REALIZADO'
      ? (actualQuery.data?.weeks ?? []).map((w) => ({
          weekIndex: w.weekIndex,
          weekStart: w.weekStart,
          weekEnd: w.weekEnd,
          inflows: w.inflows,
          outflows: w.outflows,
          net: w.net,
          balance: w.closingBalance,
        }))
      : (forecastQuery.data?.weeks ?? []).map((w) => ({
          weekIndex: w.weekIndex,
          weekStart: w.weekStart,
          weekEnd: w.weekEnd,
          inflows: w.inflows,
          outflows: w.outflows,
          net: w.net,
          balance: w.projectedBalance,
        }))

  const columns: TableColumn<WeekRow>[] = [
    { key: 'week', header: 'Semana', render: (row) => `S${row.weekIndex + 1} · ${row.weekStart} → ${row.weekEnd}` },
    { key: 'in', header: 'Entradas', render: (row) => money(row.inflows) },
    { key: 'out', header: 'Salidas', render: (row) => money(row.outflows) },
    { key: 'net', header: 'Neto', render: (row) => money(row.net) },
    {
      key: 'bal',
      header: mode === 'REALIZADO' ? 'Saldo al cierre' : 'Saldo proyectado',
      render: (row) => (
        <span style={{ color: row.balance < 0 ? '#dc2626' : undefined, fontWeight: 600 }}>
          {money(row.balance)}
        </span>
      ),
    },
  ]

  const forecast = forecastQuery.data
  const actual = actualQuery.data

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <p className="nx-page__eyebrow">Tesorería</p>
          <h1 className="nx-dashboard__title">Flujo de caja · 13 semanas</h1>
          <p className="nx-field__hint">
            {mode === 'REALIZADO'
              ? 'Movimiento REAL de las cuentas de tesorería en las últimas 13 semanas, clasificado por origen. Un aporte de capital o un financiamiento es entrada de caja pero no es ingreso contable.'
              : 'Posición de caja actual + cobros esperados (AR abierto) − pagos comprometidos (AP abierto). Solo compromisos ya registrados, sin proyección de ventas futuras.'}
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

      <Card>
        {query.isLoading ? (
          <LoadingState label={mode === 'REALIZADO' ? 'Cargando movimiento real…' : 'Proyectando 13 semanas…'} />
        ) : query.isError ? (
          <ErrorState description="No se pudo calcular el flujo de caja." onRetry={() => query.refetch()} />
        ) : rows.length > 0 ? (
          <>
            <div className="nx-treasury__actions">
              {mode === 'REALIZADO' && actual ? (
                <>
                  <Badge>Saldo inicial {money(actual.openingBalance)}</Badge>
                  <Badge tone="success">Entradas {money(actual.totalInflows)}</Badge>
                  <Badge tone="danger">Salidas {money(actual.totalOutflows)}</Badge>
                  <Badge>Saldo al cierre {money(actual.closingBalance)}</Badge>
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

            <div style={{ width: '100%', height: 260, marginTop: '0.75rem' }}>
              <ResponsiveContainer>
                <BarChart data={rows.map((w) => ({ name: `S${w.weekIndex + 1}`, saldo: w.balance }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis width={80} />
                  <Tooltip formatter={(value) => money(Number(value))} />
                  <ReferenceLine y={0} stroke="#dc2626" />
                  <Bar dataKey="saldo" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <Table columns={columns} rows={rows} getRowKey={(row) => String(row.weekIndex)} emptyMessage="Sin datos." />
          </>
        ) : (
          <EmptyState
            icon="chart"
            title={
              mode === 'REALIZADO'
                ? 'Sin movimientos de tesorería en las últimas 13 semanas'
                : 'Sin compromisos AP/AR para proyectar'
            }
          />
        )}
      </Card>
    </div>
  )
}
