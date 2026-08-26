import { useQuery } from '@tanstack/react-query'
import { Button, Card, EmptyState, ErrorState, LoadingState, Table, type TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { reportingService } from '../../services/reportingService'
import type { StatementRow } from '../../types/reporting'
import { downloadCsv, toCsv } from '../../utils/csv'

const CSV_COLUMNS = [
  { key: 'accountCode' as const, label: 'Código' },
  { key: 'accountName' as const, label: 'Cuenta' },
  { key: 'balance' as const, label: 'Monto' },
]

const COLUMNS: TableColumn<StatementRow>[] = [
  { key: 'accountCode', header: 'Código', render: (row) => row.accountCode },
  { key: 'accountName', header: 'Cuenta', render: (row) => row.accountName },
  { key: 'balance', header: 'Monto', render: (row) => row.balance },
]

/** NXR-REQ-0016/0093 (Cash Flow, método directo): entradas/salidas de
 * efectivo clasificadas por actividad Operativa/Inversión/Financiamiento
 * vía `Account.cashFlowActivity` (sin pantalla dedicada de catálogo
 * contable todavía -- se clasifica por API, mismo criterio que Tax Codes
 * antes de tener un consumidor de UI). "Sin clasificar" se muestra
 * explícito, nunca oculto -- ver reporting_service.cash_flow_statement. */
export function CashFlowPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()

  const reportQuery = useQuery({
    queryKey: ['reports', 'cash-flow', activeCompanyId],
    queryFn: () => reportingService.getCashFlow(activeCompanyId as string),
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
  const allRows = report
    ? [...report.operating, ...report.investing, ...report.financing, ...report.unclassified]
    : []

  const handleExport = () => {
    downloadCsv('flujo-de-efectivo.csv', toCsv(allRows, CSV_COLUMNS))
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Flujo de Efectivo</h1>
        <Button variant="secondary" disabled={allRows.length === 0} onClick={handleExport}>
          Exportar CSV
        </Button>
      </header>

      {reportQuery.isLoading ? (
        <LoadingState label="Cargando flujo de efectivo…" />
      ) : reportQuery.isError ? (
        <ErrorState onRetry={() => reportQuery.refetch()} />
      ) : report ? (
        <>
          <Card>
            <h2 className="nx-field__label">Actividades operativas</h2>
            <Table
              columns={COLUMNS}
              rows={report.operating}
              getRowKey={(row) => row.accountId}
              emptyMessage="Sin movimiento operativo clasificado en el período."
            />
            <p className="nx-field__label">Total operativo: {report.totalOperating}</p>
          </Card>
          <Card>
            <h2 className="nx-field__label">Actividades de inversión</h2>
            <Table
              columns={COLUMNS}
              rows={report.investing}
              getRowKey={(row) => row.accountId}
              emptyMessage="Sin movimiento de inversión clasificado en el período."
            />
            <p className="nx-field__label">Total inversión: {report.totalInvesting}</p>
          </Card>
          <Card>
            <h2 className="nx-field__label">Actividades de financiamiento</h2>
            <Table
              columns={COLUMNS}
              rows={report.financing}
              getRowKey={(row) => row.accountId}
              emptyMessage="Sin movimiento de financiamiento clasificado en el período."
            />
            <p className="nx-field__label">Total financiamiento: {report.totalFinancing}</p>
          </Card>
          {report.unclassified.length > 0 ? (
            <Card>
              <h2 className="nx-field__label">Sin clasificar</h2>
              <p className="nx-field__hint">
                Estas cuentas todavía no tienen una actividad de Cash Flow asignada
                (clasifícalas vía la API de catálogo contable) -- no se ocultan ni se
                adivinan.
              </p>
              <Table
                columns={COLUMNS}
                rows={report.unclassified}
                getRowKey={(row) => row.accountId}
                emptyMessage="Sin cuentas por clasificar."
              />
              <p className="nx-field__label">Total sin clasificar: {report.totalUnclassified}</p>
            </Card>
          ) : null}
          <Card>
            <p className="nx-field__label">Cambio neto en efectivo: {report.netChangeInCash}</p>
          </Card>
        </>
      ) : null}
    </div>
  )
}
