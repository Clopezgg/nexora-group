import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Badge,
  Card,
  CompanySelector,
  EmptyState,
  ErrorState,
  LoadingState,
  Select,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import {
  transactionInspectorService,
  type InspectedLine,
} from '../../services/transactionInspectorService'
import { formatMoney } from '../../utils/currency'
import { statusLabel } from '../../utils/statusLabels'
import './TransactionInspectorPage.css'

export function TransactionInspectorPage() {
  const { companies, activeCompanyId, setActiveCompanyId, activeCompany, isLoading, isError, refetch } =
    useActiveCompany()
  const currency = activeCompany?.functionalCurrencyCode ?? undefined
  const [searchParams] = useSearchParams()
  const [documentId, setDocumentId] = useState(searchParams.get('documentId') ?? '')

  const documentsQuery = useQuery({
    queryKey: ['accounting', 'journal-documents', activeCompanyId],
    queryFn: () => transactionInspectorService.listDocuments(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const inspectQuery = useQuery({
    queryKey: ['transaction-inspector', documentId],
    queryFn: () => transactionInspectorService.inspect(documentId),
    enabled: Boolean(documentId),
  })

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return (
      <EmptyState icon="search" title="Configura una compañía primero" description="El Transaction Inspector necesita una compañía." />
    )
  }

  const inspection = inspectQuery.data
  const lineColumns: TableColumn<InspectedLine>[] = [
    { key: 'account', header: 'Cuenta', render: (row) => `${row.accountCode} — ${row.accountName}` },
    { key: 'debit', header: 'Débito', render: (row) => (row.debit ? formatMoney(row.debit, currency) : '') },
    { key: 'credit', header: 'Crédito', render: (row) => (row.credit ? formatMoney(row.credit, currency) : '') },
    { key: 'project', header: 'Proyecto', render: (row) => row.projectName ?? '—' },
    { key: 'cc', header: 'Centro de costo', render: (row) => row.costCenterName ?? '—' },
    { key: 'desc', header: 'Glosa', render: (row) => row.description ?? '—' },
  ]

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <p className="nx-page__eyebrow">Finanzas</p>
          <h1 className="nx-dashboard__title">Transaction Inspector</h1>
          <p className="nx-field__hint">
            Drill-down inverso: del asiento del GL al evento de negocio que lo originó, con su cadena de
            reversos y evidencia.
          </p>
        </div>
        <CompanySelector
          options={companies.map((company) => ({ id: company.id, label: company.name }))}
          value={activeCompanyId}
          onChange={(value) => {
            setActiveCompanyId(value)
            setDocumentId('')
          }}
        />
      </header>

      <Card title="Asiento contable">
        {documentsQuery.isLoading ? (
          <LoadingState label="Cargando asientos…" />
        ) : (
          <Select label="Asiento a inspeccionar" value={documentId} onChange={(event) => setDocumentId(event.target.value)}>
            <option value="">Selecciona un asiento…</option>
            {(documentsQuery.data ?? []).map((document) => (
              <option key={document.id} value={document.id}>
                {document.documentNumber} — {document.description ?? document.scope} — {statusLabel(document.status)}
              </option>
            ))}
          </Select>
        )}
      </Card>

      {documentId ? (
        <Card title="Inspección">
          {inspectQuery.isLoading ? (
            <LoadingState label="Reconstruyendo la transacción…" />
          ) : inspectQuery.isError ? (
            <ErrorState description="No se pudo inspeccionar el asiento." onRetry={() => inspectQuery.refetch()} />
          ) : inspection ? (
            <>
              <div className="nx-treasury__actions">
                <Badge>{inspection.documentNumber}</Badge>
                <Badge tone={inspection.balanced ? 'success' : 'danger'}>
                  {inspection.balanced ? 'Doble partida OK' : 'DESCUADRE'}
                </Badge>
                <Badge>{statusLabel(inspection.status)}</Badge>
                <span>{inspection.currencyCode}</span>
              </div>

              <dl className="nx-detail-list">
                <div>
                  <dt>Evento de negocio (drill-down inverso)</dt>
                  <dd>
                    {inspection.sourceEvent.label}
                    {inspection.sourceEvent.reference ? ` · ${inspection.sourceEvent.reference}` : ''}
                  </dd>
                </div>
                <div>
                  <dt>Ámbito</dt>
                  <dd>{inspection.scope}</dd>
                </div>
                <div>
                  <dt>Proyecto</dt>
                  <dd>{inspection.projectName ?? 'No aplica'}</dd>
                </div>
                <div>
                  <dt>Posteado</dt>
                  <dd>{inspection.postedAt ? new Date(inspection.postedAt).toLocaleString('es-HN') : 'Sin postear'}</dd>
                </div>
                {inspection.reversesDocumentId ? (
                  <div>
                    <dt>Este asiento revierte</dt>
                    <dd>
                      <Link to="/finanzas/contabilidad">Documento {inspection.reversesDocumentId}</Link>
                      {inspection.reversalReason ? ` · Motivo: ${inspection.reversalReason}` : ''}
                    </dd>
                  </div>
                ) : null}
                {inspection.reversedByDocumentIds.length > 0 ? (
                  <div>
                    <dt>Este asiento fue revertido por</dt>
                    <dd>{inspection.reversedByDocumentIds.join(', ')}</dd>
                  </div>
                ) : null}
                {inspection.evidence.length > 0 ? (
                  <div>
                    <dt>Evidencia adjunta</dt>
                    <dd>{inspection.evidence.map((e) => e.originalFilename).join(', ')}</dd>
                  </div>
                ) : null}
              </dl>

              <Table
                columns={lineColumns}
                rows={inspection.lines}
                getRowKey={(row) => `${row.accountCode}:${row.debit}:${row.credit}:${row.description ?? ''}`}
                emptyMessage="Sin líneas."
              />
              <p className="nx-field__hint">
                Total débito {formatMoney(inspection.totalDebit, currency)} · Total crédito{' '}
                {formatMoney(inspection.totalCredit, currency)}
              </p>
            </>
          ) : null}
        </Card>
      ) : null}
    </div>
  )
}
