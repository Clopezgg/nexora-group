import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Tooltip, XAxis, YAxis } from 'recharts'
import { ChartCard } from '../../design-system'
import type { CashFlowPoint, ScopeAmount } from '../../types/dashboard'
import { formatMoney, formatMoneyCompact } from '../../utils/currency'

const scopeLabels: Record<string, string> = {
  CENTRAL: 'Central',
  GENERAL: 'General',
  PROJECT: 'Proyecto',
}

const scopeColors: Record<string, string> = {
  CENTRAL: '#1d5fd6',
  GENERAL: '#0f766e',
  PROJECT: '#7c3aed',
}

interface FinancialChartsProps {
  cashFlow: CashFlowPoint[]
  expensesByScope: ScopeAmount[]
  currency: string
}

/** Gráficas del dashboard, rediseñadas para móvil (§19/§20): ejes abreviados
 * (L 250K / L 1.2M), tooltip con el monto exacto, barras horizontales para
 * "Gastos por alcance" (no donut), y estados vacíos compactos. */
export default function FinancialCharts({ cashFlow, expensesByScope, currency }: FinancialChartsProps) {
  const scopeData = expensesByScope
    .map((item) => ({ ...item, label: scopeLabels[item.scope] ?? item.scope }))
    .filter((item) => item.amount !== 0)
  const hasCashFlow = cashFlow.some((item) => item.income !== 0 || item.expense !== 0)
  const abbreviate = (value: number | string) => formatMoneyCompact(value, currency)
  const exact = (value: number | string) => formatMoney(Number(value), currency)

  return (
    <section className="nx-home__charts" aria-label="Visualizaciones financieras">
      <ChartCard
        title="Ingresos vs. gastos"
        subtitle="Últimos seis meses"
        hasData={hasCashFlow}
        height={220}
        emptyMessage="Sin movimientos en este período."
      >
        <LineChart data={cashFlow} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e6ecf3" />
          <XAxis dataKey="period" tick={{ fontSize: 11 }} tickMargin={6} />
          <YAxis tick={{ fontSize: 11 }} width={52} tickFormatter={abbreviate} tickCount={4} />
          <Tooltip formatter={(value) => exact(Number(value))} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Line type="monotone" dataKey="income" name="Ingresos" stroke="#0f9f6e" strokeWidth={2.5} dot={false} />
          <Line type="monotone" dataKey="expense" name="Gastos" stroke="#dc3f50" strokeWidth={2.5} dot={false} />
        </LineChart>
      </ChartCard>

      <ChartCard
        title="Gastos por alcance"
        subtitle="Período actual"
        hasData={scopeData.length > 0}
        height={220}
        emptyMessage="Sin gastos registrados por alcance."
      >
        <BarChart data={scopeData} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e6ecf3" />
          <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={abbreviate} tickCount={4} />
          <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={70} />
          <Tooltip formatter={(value) => exact(Number(value))} />
          <Bar dataKey="amount" name="Gasto" radius={[0, 4, 4, 0]} barSize={22}>
            {scopeData.map((item) => (
              <Cell key={item.scope} fill={scopeColors[item.scope] ?? '#64748b'} />
            ))}
          </Bar>
        </BarChart>
      </ChartCard>
    </section>
  )
}
