import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import {
  Card,
  Drawer,
  EmptyState,
  ErrorState,
  FilterBar,
  Input,
  LoadingState,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { auditService } from '../../services/auditService'
import type { AuditLogEntry } from '../../types/audit'
import './AuditLogPage.css'
import { auditActorLabel, humanizeAuditAction, redactSensitive } from './humanizeAudit'

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('es-HN')
}

export function AuditLogPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const [entityTypeFilter, setEntityTypeFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [selected, setSelected] = useState<AuditLogEntry | null>(null)

  const auditQuery = useQuery({
    queryKey: ['audit', activeCompanyId, entityTypeFilter],
    queryFn: () =>
      auditService.list({
        companyId: activeCompanyId as string,
        entityType: entityTypeFilter || undefined,
      }),
    enabled: Boolean(activeCompanyId),
  })

  const filteredRows = useMemo(() => {
    const rows = auditQuery.data ?? []
    return rows.filter((row) => {
      if (dateFrom && row.createdAt < dateFrom) return false
      if (dateTo && row.createdAt > `${dateTo}T23:59:59`) return false
      return true
    })
  }, [auditQuery.data, dateFrom, dateTo])

  const columns: TableColumn<AuditLogEntry>[] = [
    { key: 'createdAt', header: 'Fecha', render: (row) => formatDateTime(row.createdAt) },
    { key: 'event', header: 'Evento', render: (row) => humanizeAuditAction(row.action).event },
    { key: 'module', header: 'Módulo', render: (row) => humanizeAuditAction(row.action).module },
    { key: 'actor', header: 'Ejecutado por', render: (row) => auditActorLabel(row) },
    {
      key: 'details',
      header: 'Detalle',
      render: (row) => (
        <button
          type="button"
          className="nx-button nx-button--secondary"
          onClick={() => setSelected(row)}
        >
          <span className="nx-button__label">Ver detalles</span>
        </button>
      ),
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="search"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

  const human = selected ? humanizeAuditAction(selected.action) : null

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Auditoría</h1>
      </header>

      <Card>
        <FilterBar
          onClear={() => {
            setEntityTypeFilter('')
            setDateFrom('')
            setDateTo('')
          }}
        >
          <Input
            label="Tipo de entidad"
            placeholder="ej. ap.supplier_invoice"
            value={entityTypeFilter}
            onChange={(e) => setEntityTypeFilter(e.target.value)}
          />
          <Input label="Desde" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <Input label="Hasta" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </FilterBar>

        {auditQuery.isLoading ? (
          <LoadingState label="Cargando bitácora de auditoría…" />
        ) : auditQuery.isError ? (
          <ErrorState onRetry={() => auditQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={filteredRows}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay registros de auditoría que coincidan con los filtros."
          />
        )}
      </Card>

      <Drawer open={Boolean(selected)} title="Detalle de auditoría" onClose={() => setSelected(null)}>
        {selected && human ? (
          <dl className="nx-detail-list">
            <div>
              <dt>Evento</dt>
              <dd>{human.event}</dd>
            </div>
            <div>
              <dt>Módulo</dt>
              <dd>{human.module}</dd>
            </div>
            <div>
              <dt>Fecha y hora</dt>
              <dd>{formatDateTime(selected.createdAt)}</dd>
            </div>
            <div>
              <dt>Ejecutado por</dt>
              <dd>
                {auditActorLabel(selected)}
                {selected.actorEmail ? ` · ${selected.actorEmail}` : ''}
              </dd>
            </div>
            <div>
              <dt>Código técnico del evento</dt>
              <dd><code>{selected.action}</code></dd>
            </div>
            <div>
              <dt>Registro</dt>
              <dd>{human.record}</dd>
            </div>
            <div>
              <dt>ID de entidad</dt>
              <dd><code>{selected.entityId}</code></dd>
            </div>
            <div>
              <dt>ID de correlación</dt>
              <dd><code>{selected.correlationId}</code></dd>
            </div>
            {selected.projectId ? (
              <div>
                <dt>Proyecto</dt>
                <dd><code>{selected.projectId}</code></dd>
              </div>
            ) : null}
            <div>
              <dt>Antes</dt>
              <dd>
                <pre className="nx-code-block">
                  {selected.before
                    ? JSON.stringify(redactSensitive(selected.before), null, 2)
                    : '—'}
                </pre>
              </dd>
            </div>
            <div>
              <dt>Después</dt>
              <dd>
                <pre className="nx-code-block">
                  {selected.after
                    ? JSON.stringify(redactSensitive(selected.after), null, 2)
                    : '—'}
                </pre>
              </dd>
            </div>
          </dl>
        ) : null}
      </Drawer>
    </div>
  )
}
