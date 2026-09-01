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
import { formatMoney, formatMoneyCompact } from '../../../utils/currency'
import type { CashFlowRow } from './useCashFlowSeries'

export interface CashFlowChartProps {
  rows: CashFlowRow[]
  currency: string
  height?: number
  /** Called with the drilled period when a REALIZADO bar/point is clicked. */
  onSelectPeriod?: (row: CashFlowRow) => void
}

interface ChartDatum {
  key: string
  Entradas: number
  Salidas: number
  Saldo: number
  _row: CashFlowRow
}

/**
 * Gráfico compartido de flujo de caja (ORDEN MAESTRA §10/§11): ComposedChart con
 * Entradas / Salidas / Saldo, ejes de calendario reales. Lo usan Home y la
 * página completa — una sola implementación.
 */
export function CashFlowChart({ rows, currency, height = 260, onSelectPeriod }: CashFlowChartProps) {
  const data: ChartDatum[] = rows.map((row) => ({
    key: row.key,
    Entradas: row.inflows,
    Salidas: -Math.abs(row.outflows),
    Saldo: row.balance,
    _row: row,
  }))
  const compact = (v: number | string) => formatMoneyCompact(v, currency)
  const exact = (v: number | string) => formatMoney(Number(v), currency)

  return (
    <div style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={data}
          margin={{ top: 8, right: 12, left: 4, bottom: 0 }}
          onClick={(state) => {
            if (!onSelectPeriod) return
            const payload = (
              state as { activePayload?: Array<{ payload?: ChartDatum }> }
            )?.activePayload?.[0]?.payload
            if (payload?._row.period) onSelectPeriod(payload._row)
          }}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--nx-chart-grid, #e6ecf3)" />
          <XAxis dataKey="key" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 10 }} width={64} tickFormatter={compact} />
          <Tooltip
            formatter={(value) => exact(Math.abs(Number(value)))}
            labelFormatter={(label) => {
              const row = data.find((d) => d.key === label)?._row
              return row && row.movementCount > 0
                ? `${row.key} · ${row.movementCount} movimiento(s)`
                : String(label)
            }}
          />
          <Legend wrapperStyle={{ fontSize: 10 }} />
          <ReferenceLine y={0} stroke="var(--nx-color-border-strong, #b9c9dc)" />
          <Bar dataKey="Entradas" fill="var(--nx-color-positive, #0f9f6e)" barSize={10} radius={[3, 3, 0, 0]} />
          <Bar dataKey="Salidas" fill="var(--nx-color-negative, #dc3f50)" barSize={10} radius={[0, 0, 3, 3]} />
          <Line type="monotone" dataKey="Saldo" stroke="var(--nx-color-accent, #1769d2)" strokeWidth={2} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
