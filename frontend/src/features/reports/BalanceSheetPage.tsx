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

/** NXR-REQ-0093 (financial statements subproject): Balance General armado
 * desde reporting_service.balance_sheet, que agrega directamente sobre el
 * General Ledger y nunca devuelve un resultado desbalanceado -- ver
 * docs/superpowers/specs/2026-08-25-financial-statements-design.md. */
export function BalanceSheetPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()

  const reportQuery = useQuery({
    queryKey: ['reports', 'balance-sheet', activeCompanyId],
    queryFn: () => reportingService.getBalanceSheet(activeCompanyId as string),
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
  const allRows = report ? [...report.assets, ...report.liabilities, ...report.equity] : []

  const handleExport = () => {
    downloadCsv('balance-general.csv', toCsv(allRows, CSV_COLUMNS))
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Balance General</h1>
        <Button variant="secondary" disabled={allRows.length === 0} onClick={handleExport}>
          Exportar CSV
        </Button>
      </header>

      {reportQuery.isLoading ? (
        <LoadingState label="Cargando balance general…" />
      ) : reportQuery.isError ? (
        <ErrorState onRetry={() => reportQuery.refetch()} />
      ) : report ? (
        <>
          <Card>
            <h2 className="nx-field__label">Activos</h2>
            <Table
              columns={COLUMNS}
              rows={report.assets}
              getRowKey={(row) => row.accountId}
              emptyMessage="Sin cuentas de activo con saldo."
            />
            <p className="nx-field__label">Subtotal: {report.totalAssets}</p>
          </Card>
          <Card>
            <h2 className="nx-field__label">Pasivos</h2>
            <Table
              columns={COLUMNS}
              rows={report.liabilities}
              getRowKey={(row) => row.accountId}
              emptyMessage="Sin cuentas de pasivo con saldo."
            />
            <p className="nx-field__label">Subtotal: {report.totalLiabilities}</p>
          </Card>
          <Card>
            <h2 className="nx-field__label">Patrimonio</h2>
            <Table
              columns={COLUMNS}
              rows={report.equity}
              getRowKey={(row) => row.accountId}
              emptyMessage="Sin cuentas de patrimonio con saldo."
            />
            <p className="nx-field__label">
              Subtotal: {report.totalEquity} — Resultado del ejercicio: {report.currentEarnings} —
              Subtotal + resultado: {report.totalEquityIncludingEarnings}
            </p>
          </Card>
          <Card>
            <p className="nx-field__label">Activos: {report.totalAssets}</p>
            <p className="nx-field__label">Pasivo + Patrimonio: {report.totalLiabilitiesAndEquity}</p>
            <p className="nx-field__label">Diferencia: {report.equationDelta}</p>
          </Card>
        </>
      ) : null}
    </div>
  )
}
