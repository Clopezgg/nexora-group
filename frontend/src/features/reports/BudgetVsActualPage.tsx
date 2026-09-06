import { useQuery } from '@tanstack/react-query'
import { Button, Card, ErrorState, LoadingState, Table, type TableColumn } from '../../design-system'
import { RequiresActiveProject } from '../projects/RequiresActiveProject'
import { reportingService } from '../../services/reportingService'
import type { BudgetVsActualReport } from '../../types/reporting'
import { downloadCsv, toCsv } from '../../utils/csv'
import { ReportExportButtons } from './ReportExportButtons'
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
    { concept: 'Devengado / costo reconocido', amount: report.accrued },
    { concept: 'Pagado', amount: report.paid },
    { concept: 'Disponible', amount: report.available },
  ]
}

function BudgetVsActualReportView({ projectId }: { projectId: string }) {
  const { fmt } = useReportCurrency()
  const columns: TableColumn<BudgetVsActualRow>[] = [
    { key: 'concept', header: 'Concepto', render: (row) => row.concept },
    { key: 'amount', header: 'Monto', numeric: true, render: (row) => fmt(row.amount) },
  ]
  const reportQuery = useQuery({
    queryKey: ['reports', 'budget-vs-actual', projectId],
    queryFn: () => reportingService.getBudgetVsActual(projectId),
  })
  const rows = reportQuery.data ? toRows(reportQuery.data) : []

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Presupuesto vs. Real</h1>
        <Button variant="secondary" disabled={rows.length === 0} onClick={() => downloadCsv('presupuesto-vs-real.csv', toCsv(rows, CSV_COLUMNS))}>Exportar CSV</Button>
        <ReportExportButtons
          disabled={rows.length === 0}
          basename="presupuesto-vs-real"
          exportFile={(format) => reportingService.exportBudgetVsActual(projectId, format)}
        />
      </header>
      <Card>
        {reportQuery.isLoading ? <LoadingState label="Cargando presupuesto vs. real…" /> : reportQuery.isError ? (
          <ErrorState onRetry={() => reportQuery.refetch()} />
        ) : (
          <Table columns={columns} rows={rows} getRowKey={(row) => row.concept} emptyMessage="Este proyecto todavía no tiene presupuesto BASELINE." />
        )}
      </Card>
    </div>
  )
}

export function BudgetVsActualPage() {
  return <RequiresActiveProject>{(activeProjectId) => <BudgetVsActualReportView projectId={activeProjectId} />}</RequiresActiveProject>
}
