import { useQuery } from '@tanstack/react-query'
import { Button, Card, EmptyState, ErrorState, LoadingState, Table, type TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { reportingService } from '../../services/reportingService'
import type { StatementRow } from '../../types/reporting'
import { downloadCsv, toCsv } from '../../utils/csv'
import { ReportExportButtons } from './ReportExportButtons'
import { useReportCurrency } from './reportMoney'

const CSV_COLUMNS = [
  { key: 'accountCode' as const, label: 'Código' },
  { key: 'accountName' as const, label: 'Cuenta' },
  { key: 'balance' as const, label: 'Saldo' },
]

export function IncomeStatementPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const { fmt } = useReportCurrency()
  const columns: TableColumn<StatementRow>[] = [
    { key: 'accountCode', header: 'Código', render: (row) => row.accountCode },
    { key: 'accountName', header: 'Cuenta', render: (row) => row.accountName },
    { key: 'balance', header: 'Saldo', numeric: true, render: (row) => fmt(row.balance) },
  ]
  const reportQuery = useQuery({
    queryKey: ['reports', 'income-statement', activeCompanyId],
    queryFn: () => reportingService.getIncomeStatement(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) return <EmptyState icon="book" title="Configura una compañía primero" description="No hay compañías registradas todavía." />
  const report = reportQuery.data
  const allRows = report ? [...report.revenue, ...report.expenses] : []

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Estado de Resultados</h1>
        <Button variant="secondary" disabled={allRows.length === 0} onClick={() => downloadCsv('estado-de-resultados.csv', toCsv(allRows, CSV_COLUMNS))}>Exportar CSV</Button>
        <ReportExportButtons
          disabled={allRows.length === 0}
          basename="estado-de-resultados"
          exportFile={(format) => reportingService.exportIncomeStatement(activeCompanyId, format)}
        />
      </header>
      {reportQuery.isLoading ? <LoadingState label="Cargando estado de resultados…" /> : reportQuery.isError ? (
        <ErrorState onRetry={() => reportQuery.refetch()} />
      ) : report ? (
        <>
          <Card><h2 className="nx-field__label">Ingresos</h2><Table columns={columns} rows={report.revenue} getRowKey={(row) => row.accountId} emptyMessage="Sin cuentas de ingreso con saldo." /><p className="nx-field__label">Total ingresos: {fmt(report.totalRevenue)}</p></Card>
          <Card><h2 className="nx-field__label">Gastos</h2><Table columns={columns} rows={report.expenses} getRowKey={(row) => row.accountId} emptyMessage="Sin cuentas de gasto con saldo." /><p className="nx-field__label">Total gastos: {fmt(report.totalExpenses)}</p></Card>
          <Card><p className="nx-field__label">Utilidad neta: {fmt(report.netIncome)}</p></Card>
        </>
      ) : null}
    </div>
  )
}
