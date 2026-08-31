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
import { cashForecastService, type ForecastWeek } from '../../services/cashForecastService'
import { formatMoney } from '../../utils/currency'

export function CashForecastPage() {
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } =
    useActiveCompany()

  const query = useQuery({
    queryKey: ['cash-forecast', activeCompanyId],
    queryFn: () => cashForecastService.get(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return <EmptyState icon="chart" title="Configura una compañía primero" description="El forecast de caja necesita una compañía." />
  }

  const data = query.data
  const currency = data?.currencyCode
  const money = (v: number) => formatMoney(v, currency)

  const columns: TableColumn<ForecastWeek>[] = [
    { key: 'week', header: 'Semana', render: (row) => `S${row.weekIndex + 1} · ${row.weekStart} → ${row.weekEnd}` },
    { key: 'in', header: 'Entradas', render: (row) => money(row.inflows) },
    { key: 'out', header: 'Salidas', render: (row) => money(row.outflows) },
    { key: 'net', header: 'Neto', render: (row) => money(row.net) },
    {
      key: 'bal',
      header: 'Saldo proyectado',
      render: (row) => (
        <span style={{ color: row.projectedBalance < 0 ? '#dc2626' : undefined, fontWeight: 600 }}>
          {money(row.projectedBalance)}
        </span>
      ),
    },
  ]

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <p className="nx-page__eyebrow">Finanzas</p>
          <h1 className="nx-dashboard__title">Forecast de caja · 13 semanas</h1>
          <p className="nx-field__hint">
            Posición de caja actual + cobros esperados (AR abierto) − pagos comprometidos (AP abierto y
            sus cuotas). Solo compromisos ya registrados, sin proyección de ventas futuras.
          </p>
        </div>
        <CompanySelector
          options={companies.map((company) => ({ id: company.id, label: company.name }))}
          value={activeCompanyId}
          onChange={setActiveCompanyId}
        />
      </header>

      <Card>
        {query.isLoading ? (
          <LoadingState label="Proyectando 13 semanas…" />
        ) : query.isError ? (
          <ErrorState description="No se pudo calcular el forecast." onRetry={() => query.refetch()} />
        ) : data ? (
          <>
            <div className="nx-treasury__actions">
              <Badge>Saldo inicial {money(data.openingBalance)}</Badge>
              {data.hasLiquidityAlert ? (
                <Badge tone="danger">
                  Alerta de liquidez · descubierto en la semana {(data.firstNegativeWeekIndex ?? 0) + 1} ·
                  mínimo {money(data.minProjectedBalance)}
                </Badge>
              ) : (
                <Badge tone="success">Sin descubierto proyectado en el horizonte</Badge>
              )}
            </div>

            <div style={{ width: '100%', height: 260, marginTop: '0.75rem' }}>
              <ResponsiveContainer>
                <BarChart data={data.weeks.map((w) => ({ name: `S${w.weekIndex + 1}`, saldo: w.projectedBalance }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis width={80} />
                  <Tooltip formatter={(value) => money(Number(value))} />
                  <ReferenceLine y={0} stroke="#dc2626" />
                  <Bar dataKey="saldo" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <Table columns={columns} rows={data.weeks} getRowKey={(row) => String(row.weekIndex)} emptyMessage="Sin datos." />
          </>
        ) : null}
      </Card>
    </div>
  )
}
