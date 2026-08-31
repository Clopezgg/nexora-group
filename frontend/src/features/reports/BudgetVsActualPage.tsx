import { useQuery } from '@tanstack/react-query'
import { Button, Card, ErrorState, LoadingState, Table, type TableColumn } from '../../design-system'
import { RequiresActiveProject } from '../projects/RequiresActiveProject'
import { reportingService } from '../../services/reportingService'
import type { BudgetVsActualReport } from '../../types/reporting'
import { downloadCsv, toCsv } from '../../utils/csv'
import { useReportCurrency } from './reportMoney'

interface BudgetVsActualRow {
  concept: string
  amount: string
  [key: string]: unknown
}

const CSV_COLUMNS = [
  { key: 'concept' as const, label: 'Concepto' },
  { key: 'amount' as const, label: 'Monto' },
]

function toRows(report: BudgetVsActualReport): BudgetVsActualRow[] {
  return [
    { concept: 'Autorizado', amount: report.authorized },
    { concept: 'Comprometido', amount: report.committed },
    { concept: 'Devengado', amount: report.accrued },
    { concept: 'Pagado', amount: report.paid },
    { concept: 'Disponible', amount: report.available },
  ]
}

/** NXR-REQ-0093 (alcance de esta fase): reshape puro de
 * budget_service.compute_summary para el proyecto activo (ActiveUIContext,
 * ver CLAUDE.md §7) -- nunca recalcula nada, solo redistribuye los mismos
 * campos ya confiables de GET /api/reports/budget-vs-actual. Earned
 * Value (CPI/SPI/EAC/VAC) queda fuera de alcance de este reporte. */
function BudgetVsActualReportView({ projectId }: { projectId: string }) {
  const { fmt } = useReportCurrency()
  const COLUMNS: TableColumn<BudgetVsActualRow>[] = [
    { key: 'concept', header: 'Concepto', render: (row) => row.concept },
    { key: 'amount', header: 'Monto', numeric: true, render: (row) => fmt(row.amount) },
  ]
  const reportQuery = useQuery({
    queryKey: ['reports', 'budget-vs-actual', projectId],
    queryFn: () => reportingService.getBudgetVsActual(projectId),
  })

  const rows = reportQuery.data ? toRows(reportQuery.data) : []

  const handleExport = () => {
    downloadCsv('presupuesto-vs-real.csv', toCsv(rows, CSV_COLUMNS))
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Presupuesto vs. Real</h1>
        <Button variant="secondary" disabled={rows.length === 0} onClick={handleExport}>
          Exportar CSV
        </Button>
      </header>

      <Card>
        {reportQuery.isLoading ? (
          <LoadingState label="Cargando presupuesto vs. real…" />
        ) : reportQuery.isError ? (
          <ErrorState onRetry={() => reportQuery.refetch()} />
        ) : (
          <Table
            columns={COLUMNS}
            rows={rows}
            getRowKey={(row) => row.concept}
            emptyMessage="Este proyecto todavía no tiene presupuesto BASELINE."
          />
        )}
      </Card>
    </div>
  )
}

export function BudgetVsActualPage() {
  return (
    <RequiresActiveProject>
      {(activeProjectId) => <BudgetVsActualReportView projectId={activeProjectId} />}
    </RequiresActiveProject>
  )
}
