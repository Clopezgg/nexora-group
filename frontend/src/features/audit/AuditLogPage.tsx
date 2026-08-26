import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import {
  Card,
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

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('es-HN')
}

function formatDiff(entry: AuditLogEntry): string {
  const parts: string[] = []
  if (entry.before) parts.push(`antes: ${JSON.stringify(entry.before)}`)
  if (entry.after) parts.push(`después: ${JSON.stringify(entry.after)}`)
  return parts.join(' — ') || '—'
}

export function AuditLogPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const [entityTypeFilter, setEntityTypeFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

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
    { key: 'action', header: 'Acción', render: (row) => row.action },
    { key: 'entityType', header: 'Entidad', render: (row) => row.entityType },
    { key: 'entityId', header: 'ID de entidad', render: (row) => row.entityId },
    { key: 'actorUserId', header: 'Usuario', render: (row) => row.actorUserId ?? 'sistema' },
    { key: 'diff', header: 'Cambio', render: (row) => formatDiff(row) },
    { key: 'correlationId', header: 'Correlación', render: (row) => row.correlationId },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="🔍"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

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
    </div>
  )
}
