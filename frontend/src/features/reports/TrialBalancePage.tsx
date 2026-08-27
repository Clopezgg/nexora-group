import { useQuery } from '@tanstack/react-query'
import { Button, Card, EmptyState, ErrorState, LoadingState, Table, type TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { reportingService } from '../../services/reportingService'
import type { TrialBalanceRow } from '../../types/reporting'
import { downloadCsv, toCsv } from '../../utils/csv'

const CSV_COLUMNS = [
  { key: 'accountCode' as const, label: 'Código' },
  { key: 'accountName' as const, label: 'Cuenta' },
  { key: 'debitBalance' as const, label: 'Débito' },
  { key: 'creditBalance' as const, label: 'Crédito' },
]

const COLUMNS: TableColumn<TrialBalanceRow>[] = [
  { key: 'accountCode', header: 'Código', render: (row) => row.accountCode },
  { key: 'accountName', header: 'Cuenta', render: (row) => row.accountName },
  { key: 'debitBalance', header: 'Débito', render: (row) => row.debitBalance },
  { key: 'creditBalance', header: 'Crédito', render: (row) => row.creditBalance },
]

/** NXR-REQ-0093 (alcance de esta fase): Balance de Comprobación real,
 * armado a partir de treasury_service.account_balance por cada cuenta del
 * chart of accounts de la company activa -- ver
 * backend/app/services/reporting_service.py. Balance Sheet / P&L / Cash
 * Flow quedan fuera de alcance deliberadamente. */
export function TrialBalancePage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()

  const reportQuery = useQuery({
    queryKey: ['reports', 'trial-balance', activeCompanyId],
    queryFn: () => reportingService.getTrialBalance(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="book"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

  const rows = reportQuery.data?.rows ?? []

  const handleExport = () => {
    downloadCsv('balance-de-comprobacion.csv', toCsv(rows, CSV_COLUMNS))
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Balance de Comprobación</h1>
        <Button variant="secondary" disabled={rows.length === 0} onClick={handleExport}>
          Exportar CSV
        </Button>
      </header>

      <Card>
        {reportQuery.isLoading ? (
          <LoadingState label="Cargando balance de comprobación…" />
        ) : reportQuery.isError ? (
          <ErrorState onRetry={() => reportQuery.refetch()} />
        ) : (
          <>
            <Table
              columns={COLUMNS}
              rows={rows}
              getRowKey={(row) => row.accountCode}
              emptyMessage="No hay movimientos contabilizados todavía."
            />
            {reportQuery.data ? (
              <p className="nx-field__label">
                Total débito: {reportQuery.data.totalDebit} — Total crédito: {reportQuery.data.totalCredit}
              </p>
            ) : null}
          </>
        )}
      </Card>
    </div>
  )
}
