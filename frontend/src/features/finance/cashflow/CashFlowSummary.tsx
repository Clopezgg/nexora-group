import { Badge } from '../../../design-system'
import { formatMoney } from '../../../utils/currency'
import type { CashFlowSummaryData } from './useCashFlowSeries'

export interface CashFlowSummaryProps {
  summary: CashFlowSummaryData
}

/**
 * Resumen visible (ORDEN MAESTRA §6/§7): Entradas / Salidas / Neto / Saldo del
 * rango — información, no solo tooltip. Rango de fechas reales, nunca "S1–S13".
 */
export function CashFlowSummary({ summary }: CashFlowSummaryProps) {
  const money = (v: number) => formatMoney(v, summary.currencyCode)
  return (
    <div className="nx-cashflow-summary nx-treasury__actions">
      <Badge>Saldo inicial {money(summary.openingBalance)}</Badge>
      <Badge tone="success">Entradas {money(summary.totalInflows)}</Badge>
      <Badge tone="danger">Salidas {money(summary.totalOutflows)}</Badge>
      <Badge tone={summary.net < 0 ? 'danger' : 'neutral'}>Neto {money(summary.net)}</Badge>
      <Badge>Saldo al cierre {money(summary.closingBalance)}</Badge>
      {summary.dateFrom && summary.dateTo ? (
        <Badge tone="neutral">
          {summary.dateFrom} → {summary.dateTo}
          {summary.granularityLabel ? ` · ${summary.granularityLabel}` : ''}
        </Badge>
      ) : null}
      {summary.liquidityAlert ? (
        <Badge tone="danger">
          Alerta de liquidez · mínimo {money(summary.liquidityAlert.minBalance)}
          {summary.liquidityAlert.firstNegativeLabel
            ? ` · descubierto desde ${summary.liquidityAlert.firstNegativeLabel}`
            : ''}
        </Badge>
      ) : null}
    </div>
  )
}
