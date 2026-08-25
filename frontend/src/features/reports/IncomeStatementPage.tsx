import { useQuery } from '@tanstack/react-query'
import { Button, Card, EmptyState, ErrorState, LoadingState, Table, type TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { reportingService } from '../../services/reportingService'
import type { StatementRow } from '../../types/reporting'
import { downloadCsv, toCsv } from '../../utils/csv'

const CSV_COLUMNS = [
  { key: 'accountCode' as const, label: 'Código' },
  { key: 'accountName' as const, label: 'Cuenta' },
  { key: 'balance' as const, label: 'Saldo' },
]

const COLUMNS: TableColumn<StatementRow>[] = [
  { key: 'accountCode', header: 'Código', render: (row) => row.accountCode },
  { key: 'accountName', header: 'Cuenta', render: (row) => row.accountName },
  { key: 'balance', header: 'Saldo', render: (row) => row.balance },
]

/** NXR-REQ-0093 (financial statements subproject): Estado de Resultados
 * armado desde reporting_service.income_statement -- ingresos y gastos con
 * signo natural, ver
 * docs/superpowers/specs/2026-08-25-financial-statements-design.md. */
export function IncomeStatementPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()

  const reportQuery = useQuery({
    queryKey: ['reports', 'income-statement', activeCompanyId],
    queryFn: () => reportingService.getIncomeStatement(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="📗"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

  const report = reportQuery.data
  const allRows = report ? [...report.revenue, ...report.expenses] : []

  const handleExport = () => {
    downloadCsv('estado-de-resultados.csv', toCsv(allRows, CSV_COLUMNS))
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Estado de Resultados</h1>
        <Button variant="secondary" disabled={allRows.length === 0} onClick={handleExport}>
          Exportar CSV
        </Button>
      </header>

      {reportQuery.isLoading ? (
        <LoadingState label="Cargando estado de resultados…" />
      ) : reportQuery.isError ? (
        <ErrorState onRetry={() => reportQuery.refetch()} />
      ) : report ? (
        <>
          <Card>
            <h2 className="nx-field__label">Ingresos</h2>
            <Table
              columns={COLUMNS}
              rows={report.revenue}
              getRowKey={(row) => row.accountId}
              emptyMessage="Sin cuentas de ingreso con saldo."
            />
            <p className="nx-field__label">Total ingresos: {report.totalRevenue}</p>
          </Card>
          <Card>
            <h2 className="nx-field__label">Gastos</h2>
            <Table
              columns={COLUMNS}
              rows={report.expenses}
              getRowKey={(row) => row.accountId}
              emptyMessage="Sin cuentas de gasto con saldo."
            />
            <p className="nx-field__label">Total gastos: {report.totalExpenses}</p>
          </Card>
          <Card>
            <p className="nx-field__label">Utilidad neta: {report.netIncome}</p>
          </Card>
        </>
      ) : null}
    </div>
  )
}
