import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Card, EmptyState, LoadingState } from '../../design-system'
import { cashForecastService } from '../../services/cashForecastService'
import { formatMoney, formatMoneyCompact } from '../../utils/currency'

/** Flujo de caja proyectado — 13 semanas, vista compacta en el Home (§15).
 * Reutiliza el servicio real `cashForecastService`; no duplica lógica. */
export function HomeForecastCard({ companyId }: { companyId: string }) {
  const query = useQuery({
    queryKey: ['financial-control', 'cash-forecast', companyId],
    queryFn: () => cashForecastService.get(companyId),
    enabled: Boolean(companyId),
  })

  const forecast = query.data
  const weeks = Array.isArray(forecast?.weeks) ? forecast.weeks : []
  const hasData = weeks.some((week) => week.inflows !== 0 || week.outflows !== 0)
  const currency = forecast?.currencyCode ?? 'HNL'
  const abbreviate = (value: number | string) => formatMoneyCompact(value, currency)
  const exact = (value: number | string) => formatMoney(Number(value), currency)

  const data = weeks.map((week) => ({
    label: `S${week.weekIndex + 1}`,
    Entradas: week.inflows,
    Salidas: -Math.abs(week.outflows),
    Saldo: week.projectedBalance,
  }))

  return (
    <Card title="Flujo de caja proyectado · 13 semanas">
      {query.isLoading ? (
        <LoadingState label="Cargando forecast…" />
      ) : !hasData ? (
        <div className="nx-home__forecast-empty">
          <EmptyState icon="chart" title="Aún no hay movimientos suficientes para proyectar 13 semanas" />
          <Link to="/finanzas/flujo-13-semanas">Abrir Forecast de caja →</Link>
        </div>
      ) : (
        <>
          {forecast?.hasLiquidityAlert ? (
            <p className="nx-field__error" role="status">
              Alerta de liquidez: saldo mínimo proyectado {exact(forecast.minProjectedBalance)}
              {forecast.firstNegativeWeekIndex != null
                ? ` (negativo desde S${forecast.firstNegativeWeekIndex + 1})`
                : ''}
              .
            </p>
          ) : null}
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e6ecf3" />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={0} />
                <YAxis tick={{ fontSize: 10 }} width={52} tickFormatter={abbreviate} />
                <Tooltip formatter={(value) => exact(Number(value))} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Bar dataKey="Entradas" fill="#0f9f6e" barSize={8} />
                <Bar dataKey="Salidas" fill="#dc3f50" barSize={8} />
                <Line type="monotone" dataKey="Saldo" stroke="#1769d2" strokeWidth={2} dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <Link to="/finanzas/flujo-13-semanas">Ver forecast completo →</Link>
        </>
      )}
    </Card>
  )
}
