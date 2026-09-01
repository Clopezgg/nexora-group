import { useState } from 'react'
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
import { cashFlowActualService } from '../../services/cashFlowActualService'
import { formatMoney, formatMoneyCompact } from '../../utils/currency'

type Mode = 'REALIZADO' | 'PROYECTADO'

/**
 * Flujo de caja en el Home (§14): [ REALIZADO | PROYECTADO ].
 * - REALIZADO: las últimas 13 semanas de movimiento real de tesorería
 *   (`cashFlowActualService`).
 * - PROYECTADO: las próximas 13 semanas proyectadas de AP/AR
 *   (`cashForecastService`).
 * Son conceptos distintos con endpoints distintos — no se mezclan: las
 * remesas históricas viven en REALIZADO, no en la S1 del forecast (el
 * opening balance del forecast ya las incluye).
 */
export function HomeForecastCard({ companyId }: { companyId: string }) {
  const [mode, setMode] = useState<Mode>('REALIZADO')

  const actualQuery = useQuery({
    queryKey: ['financial-control', 'cash-flow-actual', companyId],
    queryFn: () => cashFlowActualService.get(companyId),
    enabled: Boolean(companyId) && mode === 'REALIZADO',
  })
  const forecastQuery = useQuery({
    queryKey: ['financial-control', 'cash-forecast', companyId],
    queryFn: () => cashForecastService.get(companyId),
    enabled: Boolean(companyId) && mode === 'PROYECTADO',
  })

  const query = mode === 'REALIZADO' ? actualQuery : forecastQuery
  const currency =
    (mode === 'REALIZADO' ? actualQuery.data?.currencyCode : forecastQuery.data?.currencyCode) ?? 'HNL'
  const abbreviate = (value: number | string) => formatMoneyCompact(value, currency)
  const exact = (value: number | string) => formatMoney(Number(value), currency)

  const data: Array<{ label: string; Entradas: number; Salidas: number; Saldo: number }> =
    mode === 'REALIZADO'
      ? (actualQuery.data?.weeks ?? []).map((week) => ({
          label: `S${week.weekIndex + 1}`,
          Entradas: week.inflows,
          Salidas: -Math.abs(week.outflows),
          Saldo: week.closingBalance,
        }))
      : (forecastQuery.data?.weeks ?? []).map((week) => ({
          label: `S${week.weekIndex + 1}`,
          Entradas: week.inflows,
          Salidas: -Math.abs(week.outflows),
          Saldo: week.projectedBalance,
        }))
  const hasData = data.some((row) => row.Entradas !== 0 || row.Salidas !== 0)

  const liquidityAlert =
    mode === 'PROYECTADO' && forecastQuery.data?.hasLiquidityAlert ? forecastQuery.data : null

  return (
    <Card
      title={
        mode === 'REALIZADO'
          ? 'Flujo de caja real · últimas 13 semanas'
          : 'Flujo de caja proyectado · próximas 13 semanas'
      }
    >
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

      {query.isLoading ? (
        <LoadingState label="Cargando flujo de caja…" />
      ) : !hasData ? (
        <div className="nx-home__forecast-empty">
          <EmptyState
            icon="chart"
            title={
              mode === 'REALIZADO'
                ? 'Todavía no hay movimientos de tesorería en las últimas 13 semanas'
                : 'Aún no hay movimientos suficientes para proyectar 13 semanas'
            }
          />
          <Link to="/finanzas/flujo-13-semanas">Abrir Flujo de caja →</Link>
        </div>
      ) : (
        <>
          {liquidityAlert ? (
            <p className="nx-field__error" role="status">
              Alerta de liquidez: saldo mínimo proyectado {exact(liquidityAlert.minProjectedBalance)}
              {liquidityAlert.firstNegativeWeekIndex != null
                ? ` (negativo desde S${liquidityAlert.firstNegativeWeekIndex + 1})`
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
                <Line
                  type="monotone"
                  dataKey="Saldo"
                  stroke="#1769d2"
                  strokeWidth={2}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <Link to="/finanzas/flujo-13-semanas">Ver flujo de caja completo →</Link>
        </>
      )}
    </Card>
  )
}
