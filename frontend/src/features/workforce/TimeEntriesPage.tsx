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
  Modal,
  Select,
  StatCard,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { projectService } from '../../services/projectService'
import { workforceService } from '../../services/workforceService'
import type { TimeEntry, TimeEntryStatus, Worker } from '../../types/workforce'

const STATUS_TONE: Record<TimeEntryStatus, 'success' | 'warning' | 'danger'> = {
  SUBMITTED: 'warning',
  APPROVED: 'success',
  REJECTED: 'danger',
}

const STATUS_LABEL: Record<TimeEntryStatus, string> = {
  SUBMITTED: 'Enviado',
  APPROVED: 'Aprobado',
  REJECTED: 'Rechazado',
}

function sumLaborCost(entries: TimeEntry[]): string {
  const total = entries.reduce((acc, entry) => acc + (entry.laborCost ? Number(entry.laborCost) : 0), 0)
  return total.toFixed(2)
}

function ApproveControl({
  entry,
  onApprove,
  onReject,
  loading,
}: {
  entry: TimeEntry
  onApprove: (approvedHours: string) => void
  onReject: () => void
  loading: boolean
}) {
  const [approvedHours, setApprovedHours] = useState(entry.hoursWorked)
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      <Input
        aria-label={`Horas aprobadas para ${entry.id}`}
        value={approvedHours}
        onChange={(e) => setApprovedHours(e.target.value)}
        style={{ width: 80 }}
      />
      <Button loading={loading} onClick={() => onApprove(approvedHours)}>
        Aprobar
      </Button>
      <Button variant="ghost" disabled={loading} onClick={onReject}>
        Rechazar
      </Button>
    </div>
  )
}

export function TimeEntriesPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({
    workerId: '',
    scope: 'GENERAL' as 'CENTRAL' | 'GENERAL' | 'PROJECT',
    projectId: '',
    workDate: '',
    hoursWorked: '',
    hourlyRate: '',
  })

  const [statusFilter, setStatusFilter] = useState<'ALL' | TimeEntryStatus>('ALL')
  const [projectFilter, setProjectFilter] = useState<'ALL' | 'NONE' | string>('ALL')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const workersQuery = useQuery({
    queryKey: ['workforce', 'workers', activeCompanyId],
    queryFn: () => workforceService.listWorkers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const projectsQuery = useQuery({
    queryKey: ['projects', 'list', activeCompanyId],
    queryFn: () => projectService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const timeEntriesQuery = useQuery({
    queryKey: ['workforce', 'time-entries', activeCompanyId],
    queryFn: () => workforceService.listTimeEntries(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['workforce', 'time-entries', activeCompanyId] })
  }

  const createMutation = useMutation({
    mutationFn: () =>
      workforceService.createTimeEntry({
        companyId: activeCompanyId as string,
        workerId: form.workerId,
        scope: form.scope,
        projectId: form.scope === 'PROJECT' ? form.projectId : undefined,
        workDate: form.workDate,
        hoursWorked: form.hoursWorked,
        hourlyRate: form.hourlyRate,
      }),
    onSuccess: () => {
      invalidate()
      setModalOpen(false)
      setForm({ workerId: '', scope: 'GENERAL', projectId: '', workDate: '', hoursWorked: '', hourlyRate: '' })
    },
  })

  const approveMutation = useMutation({
    mutationFn: ({ id, approvedHours }: { id: string; approvedHours: string }) =>
      workforceService.approveTimeEntry(id, approvedHours),
    onSuccess: invalidate,
  })

  const rejectMutation = useMutation({
    mutationFn: (id: string) => workforceService.rejectTimeEntry(id),
    onSuccess: invalidate,
  })

  const workerById = useMemo(() => {
    const map = new Map<string, Worker>()
    for (const worker of workersQuery.data ?? []) map.set(worker.id, worker)
    return map
  }, [workersQuery.data])

  const projectById = useMemo(() => {
    const map = new Map<string, string>()
    for (const project of projectsQuery.data ?? []) map.set(project.id, project.name)
    return map
  }, [projectsQuery.data])

  const filteredEntries = useMemo(() => {
    return (timeEntriesQuery.data ?? []).filter((entry) => {
      if (statusFilter !== 'ALL' && entry.status !== statusFilter) return false
      if (projectFilter === 'NONE' && entry.projectId !== null) return false
      if (projectFilter !== 'ALL' && projectFilter !== 'NONE' && entry.projectId !== projectFilter) return false
      if (dateFrom && entry.workDate < dateFrom) return false
      if (dateTo && entry.workDate > dateTo) return false
      return true
    })
  }, [timeEntriesQuery.data, statusFilter, projectFilter, dateFrom, dateTo])

  const columns: TableColumn<TimeEntry>[] = [
    { key: 'workDate', header: 'Fecha', render: (row) => row.workDate },
    {
      key: 'worker',
      header: 'Trabajador',
      render: (row) => workerById.get(row.workerId)?.fullName ?? row.workerId,
    },
    { key: 'scope', header: 'Ámbito', render: (row) => row.scope },
    {
      key: 'project',
      header: 'Proyecto',
      render: (row) => (row.projectId ? projectById.get(row.projectId) ?? row.projectId : '—'),
    },
    { key: 'hoursWorked', header: 'Horas reportadas', render: (row) => row.hoursWorked },
    { key: 'hourlyRate', header: 'Tarifa / hora', render: (row) => row.hourlyRate },
    {
      key: 'status',
      header: 'Estado',
      render: (row) => <Badge tone={STATUS_TONE[row.status]}>{STATUS_LABEL[row.status]}</Badge>,
    },
    { key: 'approvedHours', header: 'Horas aprobadas', render: (row) => row.approvedHours ?? '—' },
    { key: 'laborCost', header: 'Costo de mano de obra', render: (row) => row.laborCost ?? '—' },
    {
      key: 'actions',
      header: '',
      render: (row) =>
        row.status === 'SUBMITTED' ? (
          <ApproveControl
            entry={row}
            loading={approveMutation.isPending || rejectMutation.isPending}
            onApprove={(approvedHours) => approveMutation.mutate({ id: row.id, approvedHours })}
            onReject={() => rejectMutation.mutate(row.id)}
          />
        ) : null,
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="⏱️"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

  const workers = workersQuery.data ?? []
  const projects = projectsQuery.data ?? []
  const approvedTotal = sumLaborCost(filteredEntries.filter((entry) => entry.status === 'APPROVED'))

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Tiempo</h1>
        <Button onClick={() => setModalOpen(true)}>Nuevo registro de tiempo</Button>
      </header>

      <StatCard label="Costo de mano de obra aprobado (filtro actual)" value={`L. ${approvedTotal}`} />

      <Card>
        <FilterBar
          onClear={() => {
            setStatusFilter('ALL')
            setProjectFilter('ALL')
            setDateFrom('')
            setDateTo('')
          }}
        >
          <Select
            label="Estado"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as 'ALL' | TimeEntryStatus)}
          >
            <option value="ALL">Todos</option>
            <option value="SUBMITTED">Enviado</option>
            <option value="APPROVED">Aprobado</option>
            <option value="REJECTED">Rechazado</option>
          </Select>
          <Select label="Proyecto" value={projectFilter} onChange={(e) => setProjectFilter(e.target.value)}>
            <option value="ALL">Todos</option>
            <option value="NONE">Sin proyecto</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </Select>
          <Input label="Desde" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          <Input label="Hasta" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        </FilterBar>

        {timeEntriesQuery.isLoading ? (
          <LoadingState label="Cargando registros de tiempo…" />
        ) : timeEntriesQuery.isError ? (
          <ErrorState onRetry={() => timeEntriesQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={filteredEntries}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay registros de tiempo que coincidan con los filtros."
          />
        )}
      </Card>

      <Modal open={modalOpen} title="Nuevo registro de tiempo" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Select
            label="Trabajador"
            value={form.workerId}
            onChange={(e) => {
              const workerId = e.target.value
              const worker = workerById.get(workerId)
              setForm({
                ...form,
                workerId,
                hourlyRate: worker ? worker.standardHourlyRate : form.hourlyRate,
              })
            }}
            required
          >
            <option value="">Selecciona un trabajador</option>
            {workers.map((worker) => (
              <option key={worker.id} value={worker.id}>
                {worker.fullName}
              </option>
            ))}
          </Select>
          <Select
            label="Ámbito"
            value={form.scope}
            onChange={(e) =>
              setForm({ ...form, scope: e.target.value as 'CENTRAL' | 'GENERAL' | 'PROJECT', projectId: '' })
            }
          >
            <option value="CENTRAL">Central</option>
            <option value="GENERAL">General</option>
            <option value="PROJECT">Proyecto</option>
          </Select>
          {form.scope === 'PROJECT' ? (
            <Select
              label="Proyecto"
              value={form.projectId}
              onChange={(e) => setForm({ ...form, projectId: e.target.value })}
              required
            >
              <option value="">Selecciona un proyecto</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </Select>
          ) : null}
          <Input
            label="Fecha"
            type="date"
            value={form.workDate}
            onChange={(e) => setForm({ ...form, workDate: e.target.value })}
            required
          />
          <Input
            label="Horas trabajadas"
            value={form.hoursWorked}
            onChange={(e) => setForm({ ...form, hoursWorked: e.target.value })}
            required
          />
          <Input
            label="Tarifa / hora"
            value={form.hourlyRate}
            onChange={(e) => setForm({ ...form, hourlyRate: e.target.value })}
            required
          />
          <Button type="submit" loading={createMutation.isPending}>
            Guardar
          </Button>
          {createMutation.isError ? (
            <p className="nx-field__error">{String(createMutation.error)}</p>
          ) : null}
        </form>
      </Modal>
    </div>
  )
}
