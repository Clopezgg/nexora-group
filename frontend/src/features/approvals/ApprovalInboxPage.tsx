import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  FilterBar,
  Input,
  LoadingState,
  Select,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { approvalService } from '../../services/approvalService'
import type { ApprovalPriority, ApprovalRequestEntry } from '../../types/approval'

const PRIORITY_TONE: Record<ApprovalPriority, 'success' | 'warning' | 'danger'> = {
  LOW: 'success',
  NORMAL: 'warning',
  HIGH: 'danger',
}

const PRIORITY_LABEL: Record<ApprovalPriority, string> = {
  LOW: 'Baja',
  NORMAL: 'Normal',
  HIGH: 'Alta',
}

function DecideControl({
  request,
  onDecide,
  loading,
}: {
  request: ApprovalRequestEntry
  onDecide: (decision: 'APPROVED' | 'REJECTED', comment: string) => void
  loading: boolean
}) {
  const [comment, setComment] = useState('')
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <Input
        aria-label={`Comentario para ${request.id}`}
        placeholder="Comentario (opcional)"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        style={{ width: 180 }}
      />
      <Button loading={loading} onClick={() => onDecide('APPROVED', comment)}>
        Aprobar
      </Button>
      <Button variant="ghost" disabled={loading} onClick={() => onDecide('REJECTED', comment)}>
        Rechazar
      </Button>
    </div>
  )
}

export function ApprovalInboxPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const [moduleFilter, setModuleFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState<'ALL' | ApprovalPriority>('ALL')

  const approvalsQuery = useQuery({
    queryKey: ['approvals', activeCompanyId, moduleFilter],
    queryFn: () =>
      approvalService.list({
        companyId: activeCompanyId as string,
        module: moduleFilter || undefined,
      }),
    enabled: Boolean(activeCompanyId),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['approvals', activeCompanyId, moduleFilter] })
  }

  const decideMutation = useMutation({
    mutationFn: ({
      id,
      decision,
      comment,
    }: {
      id: string
      decision: 'APPROVED' | 'REJECTED'
      comment: string
    }) => approvalService.decide(id, decision, comment),
    onSuccess: invalidate,
    onError: (error) => handleMutationError(error, 'Decidir aprobación'),
  })

  const filteredRows = useMemo(() => {
    const rows = approvalsQuery.data ?? []
    if (priorityFilter === 'ALL') return rows
    return rows.filter((row) => row.priority === priorityFilter)
  }, [approvalsQuery.data, priorityFilter])

  const columns: TableColumn<ApprovalRequestEntry>[] = [
    { key: 'module', header: 'Módulo', render: (row) => row.module },
    { key: 'entityType', header: 'Tipo de entidad', render: (row) => row.entityType },
    {
      key: 'priority',
      header: 'Prioridad',
      render: (row) => <Badge tone={PRIORITY_TONE[row.priority]}>{PRIORITY_LABEL[row.priority]}</Badge>,
    },
    { key: 'amount', header: 'Monto', render: (row) => row.amount ?? '—' },
    { key: 'requestedBy', header: 'Solicitado por', render: (row) => row.requestedBy },
    { key: 'createdAt', header: 'Fecha', render: (row) => new Date(row.createdAt).toLocaleString('es-HN') },
    {
      key: 'actions',
      header: '',
      render: (row) =>
        row.status === 'PENDING' ? (
          <DecideControl
            request={row}
            loading={decideMutation.isPending}
            onDecide={(decision, comment) => decideMutation.mutate({ id: row.id, decision, comment })}
          />
        ) : null,
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="📥"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Bandeja de aprobaciones</h1>
      </header>

      <Card>
        <FilterBar
          onClear={() => {
            setModuleFilter('')
            setPriorityFilter('ALL')
          }}
        >
          <Input
            label="Módulo"
            placeholder="ej. ap, construction"
            value={moduleFilter}
            onChange={(e) => setModuleFilter(e.target.value)}
          />
          <Select
            label="Prioridad"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value as 'ALL' | ApprovalPriority)}
          >
            <option value="ALL">Todas</option>
            <option value="LOW">Baja</option>
            <option value="NORMAL">Normal</option>
            <option value="HIGH">Alta</option>
          </Select>
        </FilterBar>

        {approvalsQuery.isLoading ? (
          <LoadingState label="Cargando bandeja de aprobaciones…" />
        ) : approvalsQuery.isError ? (
          <ErrorState onRetry={() => approvalsQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={filteredRows}
            getRowKey={(row) => row.id}
            emptyMessage="No tienes solicitudes de aprobación pendientes."
          />
        )}
      </Card>
    </div>
  )
}
