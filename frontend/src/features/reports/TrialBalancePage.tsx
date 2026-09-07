import { useQuery } from '@tanstack/react-query'
import { Button, Card, EmptyState, ErrorState, LoadingState, Table, type TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { reportingService } from '../../services/reportingService'
import type { TrialBalanceRow } from '../../types/reporting'
import { downloadCsv, toCsv } from '../../utils/csv'
import { ReportExportButtons } from './ReportExportButtons'
import { useReportCurrency } from './reportMoney'

const CSV_COLUMNS = [
  { key: 'accountCode' as const, label: 'Código' },
  { key: 'accountName' as const, label: 'Cuenta' },
  { key: 'debitBalance' as const, label: 'Débito' },
  { key: 'creditBalance' as const, label: 'Crédito' },
]

function buildColumns(
  fmt: (value: string | number | null | undefined) => string,
  onDrillToLedger?: (accountId: string, label: string) => void,
): TableColumn<TrialBalanceRow>[] {
  return [
    {
      key: 'accountCode',
      header: 'Código',
      render: (row) =>
        onDrillToLedger ? (
          <button
            type="button"
            className="nx-link-button"
            onClick={() => onDrillToLedger(row.accountId, `${row.accountCode} — ${row.accountName}`)}
          >
            {row.accountCode}
          </button>
        ) : row.accountCode,
    },
    { key: 'accountName', header: 'Cuenta', render: (row) => row.accountName },
    { key: 'debitBalance', header: 'Débito', numeric: true, render: (row) => fmt(row.debitBalance) },
    { key: 'creditBalance', header: 'Crédito', numeric: true, render: (row) => fmt(row.creditBalance) },
  ]
}

export function TrialBalancePage({
  onDrillToLedger,
}: {
  onDrillToLedger?: (accountId: string, label: string) => void
} = {}) {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const { fmt } = useReportCurrency()
  const columns = buildColumns(fmt, onDrillToLedger)
  const reportQuery = useQuery({
    queryKey: ['reports', 'trial-balance', activeCompanyId],
    queryFn: () => reportingService.getTrialBalance(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return <EmptyState icon="book" title="Configura una compañía primero" description="No hay compañías registradas todavía." />
  }

  const rows = reportQuery.data?.rows ?? []
  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Balance de Comprobación</h1>
        <Button variant="secondary" disabled={rows.length === 0} onClick={() => downloadCsv('balance-de-comprobacion.csv', toCsv(rows, CSV_COLUMNS))}>
          Exportar CSV
        </Button>
        <ReportExportButtons
          disabled={rows.length === 0}
          basename="balance-de-comprobacion"
          exportFile={(format) => reportingService.exportTrialBalance(activeCompanyId, format)}
        />
      </header>
      <Card>
        {reportQuery.isLoading ? <LoadingState label="Cargando balance de comprobación…" /> : reportQuery.isError ? (
          <ErrorState onRetry={() => reportQuery.refetch()} />
        ) : (
          <>
            <Table columns={columns} rows={rows} getRowKey={(row) => row.accountId} emptyMessage="No hay movimientos contabilizados todavía." />
            {reportQuery.data ? (
              <p className="nx-field__label">
                Total débito: {fmt(reportQuery.data.totalDebit)} — Total crédito: {fmt(reportQuery.data.totalCredit)}
              </p>
            ) : null}
          </>
        )}
      </Card>
    </div>
  )
}
