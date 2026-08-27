import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Card, EmptyState, ErrorState, LoadingState, Table, type TableColumn } from '../../design-system'
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
  { key: 'documentNumber', header: 'Documento', render: (row) => row.documentNumber },
  { key: 'postedAt', header: 'Fecha', render: (row) => row.postedAt ?? '—' },
  { key: 'accountCode', header: 'Cuenta', render: (row) => `${row.accountCode} — ${row.accountName}` },
  { key: 'description', header: 'Descripción', render: (row) => row.description ?? '—' },
  { key: 'debitAmount', header: 'Débito', render: (row) => row.debitAmount },
  { key: 'creditAmount', header: 'Crédito', render: (row) => row.creditAmount },
]

/** NXR-REQ-0093 (financial statements subproject): Libro Mayor paginado
 * real desde reporting_service.general_ledger -- los totales cubren todo
 * el filtro, no solo la página cargada. Filtros de fecha quedan fuera de
 * esta primera UI (el contrato de la API ya los soporta) -- ver
 * docs/superpowers/specs/2026-08-25-financial-statements-design.md. */
export function GeneralLedgerPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const [offset, setOffset] = useState(0)

  const reportQuery = useQuery({
    queryKey: ['reports', 'general-ledger', activeCompanyId, offset],
    queryFn: () => reportingService.getGeneralLedger(activeCompanyId as string, offset, PAGE_SIZE),
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
