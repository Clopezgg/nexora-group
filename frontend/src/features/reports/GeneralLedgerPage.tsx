import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Badge, Button, Card, EmptyState, ErrorState, LoadingState, Table, type TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { reportingService } from '../../services/reportingService'
import type { GeneralLedgerRow } from '../../types/reporting'
import { downloadCsv, toCsv } from '../../utils/csv'

const PAGE_SIZE = 25

const CSV_COLUMNS = [
  { key: 'documentNumber' as const, label: 'Documento' },
  { key: 'postedAt' as const, label: 'Fecha' },
  { key: 'accountCode' as const, label: 'Cuenta' },
  { key: 'description' as const, label: 'Descripción' },
  { key: 'debitAmount' as const, label: 'Débito' },
  { key: 'creditAmount' as const, label: 'Crédito' },
]

const COLUMNS: TableColumn<GeneralLedgerRow>[] = [
  {
    key: 'documentNumber',
    header: 'Documento',
    render: (row) => (
      <Link to={`/finanzas/inspector?documentId=${encodeURIComponent(row.documentId)}`}>
        {row.documentNumber}
      </Link>
    ),
  },
  { key: 'postedAt', header: 'Fecha', render: (row) => row.postedAt ?? '—' },
  { key: 'accountCode', header: 'Cuenta', render: (row) => `${row.accountCode} — ${row.accountName}` },
  { key: 'description', header: 'Descripción', render: (row) => row.description ?? '—' },
  { key: 'debitAmount', header: 'Débito', render: (row) => row.debitAmount },
  { key: 'creditAmount', header: 'Crédito', render: (row) => row.creditAmount },
]

/** NXR-REQ-0093 + Phase 9: Libro Mayor paginado real. Cuando se llega por
 * drill-down desde el Balance de Comprobación se filtra por cuenta; cada
 * documento enlaza al Transaction Inspector. */
export function GeneralLedgerPage({
  accountId = null,
  accountLabel = null,
  onClearAccountFilter,
}: {
  accountId?: string | null
  accountLabel?: string | null
  onClearAccountFilter?: () => void
} = {}) {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const [offset, setOffset] = useState(0)

  const reportQuery = useQuery({
    queryKey: ['reports', 'general-ledger', activeCompanyId, offset, accountId],
    queryFn: () =>
      reportingService.getGeneralLedger(activeCompanyId as string, offset, PAGE_SIZE, accountId ?? undefined),
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

  const report = reportQuery.data
  const rows = report?.rows ?? []
  const canGoPrevious = offset > 0
  const canGoNext = Boolean(report && offset + rows.length < report.total)

  const handleExport = () => {
    downloadCsv('libro-mayor.csv', toCsv(rows, CSV_COLUMNS))
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Libro Mayor</h1>
        <Button variant="secondary" disabled={rows.length === 0} onClick={handleExport}>
          Exportar CSV
        </Button>
      </header>

      {accountId ? (
        <div className="nx-treasury__actions" style={{ marginBottom: '0.5rem' }}>
          <Badge tone="info">Filtrado por cuenta: {accountLabel ?? accountId}</Badge>
          {onClearAccountFilter ? (
            <Button
              variant="secondary"
              onClick={() => {
                setOffset(0)
                onClearAccountFilter()
              }}
            >
              Quitar filtro
            </Button>
          ) : null}
        </div>
      ) : null}

      <Card>
        {reportQuery.isLoading ? (
          <LoadingState label="Cargando libro mayor…" />
        ) : reportQuery.isError ? (
          <ErrorState onRetry={() => reportQuery.refetch()} />
        ) : (
          <>
            <Table
              columns={COLUMNS}
              rows={rows}
              getRowKey={(row) => row.lineId}
              emptyMessage="No hay movimientos contabilizados todavía."
            />
            {report ? (
              <p className="nx-field__label">
                Total débito: {report.totalDebit} — Total crédito: {report.totalCredit} — {report.total} movimientos
              </p>
            ) : null}
            <div className="nx-page__header">
              <Button variant="secondary" disabled={!canGoPrevious} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                Anterior
              </Button>
              <Button variant="secondary" disabled={!canGoNext} onClick={() => setOffset(offset + PAGE_SIZE)}>
                Siguiente
              </Button>
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
