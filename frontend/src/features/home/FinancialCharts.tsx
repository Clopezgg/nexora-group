import { Cell, Legend, Line, LineChart, Pie, PieChart, Tooltip, XAxis, YAxis } from 'recharts'
import { ChartCard } from '../../design-system'
import type { CashFlowPoint, ScopeAmount } from '../../types/dashboard'
import { formatMoney } from '../../utils/currency'

const scopeLabels: Record<string, string> = {
  CENTRAL: 'Central',
  GENERAL: 'General',
  PROJECT: 'Proyecto',
}

const scopeColors: Record<string, string> = {
  CENTRAL: '#2563eb',
  GENERAL: '#0f766e',
  PROJECT: '#7c3aed',
}

interface FinancialChartsProps {
  cashFlow: CashFlowPoint[]
  expensesByScope: ScopeAmount[]
  currency: string
}

export default function FinancialCharts({
  cashFlow,
  expensesByScope,
  currency,
}: FinancialChartsProps) {
  const scopeData = expensesByScope.map((item) => ({
    ...item,
    label: scopeLabels[item.scope] ?? item.scope,
  }))
  const hasCashFlow = cashFlow.some((item) => item.income !== 0 || item.expense !== 0)

  return (
    <section className="nx-home__charts" aria-label="Visualizaciones financieras">
      <ChartCard title="Ingresos vs. gastos" subtitle="Últimos seis meses" hasData={hasCashFlow}>
        <LineChart data={cashFlow} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
          <XAxis dataKey="period" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} width={72} />
          <Tooltip formatter={(value) => formatMoney(Number(value), currency)} />
          <Legend />
          <Line type="monotone" dataKey="income" name="Ingresos" stroke="#0f9f6e" strokeWidth={2.5} dot={false} />
          <Line type="monotone" dataKey="expense" name="Gastos" stroke="#dc3f50" strokeWidth={2.5} dot={false} />
        </LineChart>
      </ChartCard>
      <ChartCard title="Gastos por alcance" subtitle="Período actual" hasData={scopeData.length > 0}>
        <PieChart>
          <Pie data={scopeData} dataKey="amount" nameKey="label" innerRadius={54} outerRadius={86} paddingAngle={2}>
            {scopeData.map((item) => (
              <Cell key={item.scope} fill={scopeColors[item.scope] ?? '#64748b'} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => formatMoney(Number(value), currency)} />
          <Legend />
        </PieChart>
      </ChartCard>
    </section>
  )
}
