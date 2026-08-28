import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Select,
  Table,
  Textarea,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { crmService } from '../../services/crmService'
import { masterDataService } from '../../services/masterDataService'
import { projectService } from '../../services/projectService'
import type { Project, ProjectStatus } from '../../types/project'
import { statusLabel } from '../../utils/statusLabels'
import { useActiveContext } from '../context/useActiveContext'

const NEXT_STATUS: Partial<Record<ProjectStatus, Array<{ status: ProjectStatus; label: string }>>> = {
  PLANNING: [
    { status: 'ACTIVE', label: 'Activar proyecto' },
    { status: 'CANCELLED', label: 'Cancelar' },
  ],
  ACTIVE: [
    { status: 'ON_HOLD', label: 'Pausar' },
    { status: 'COMPLETED', label: 'Completar' },
    { status: 'CANCELLED', label: 'Cancelar' },
  ],
  ON_HOLD: [
    { status: 'ACTIVE', label: 'Reanudar' },
    { status: 'CANCELLED', label: 'Cancelar' },
  ],
  COMPLETED: [{ status: 'CLOSED', label: 'Cerrar proyecto' }],
}

export function ProjectsPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { context, setActiveProject } = useActiveContext()
  const { activeCompany, activeCompanyId, isLoading: companiesLoading, isError: companiesError, refetch } = useActiveCompany()
  const [form, setForm] = useState({
    name: '',
    code: '',
    customerId: '',
    manager: '',
    currencyCode: 'HNL',
    plannedStart: '',
    plannedEnd: '',
    description: '',
  })

  const projectsQuery = useQuery({
    queryKey: ['projects', activeCompanyId],
    queryFn: () => projectService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const customersQuery = useQuery({
    queryKey: ['crm', 'customers', activeCompanyId],
    queryFn: () => crmService.listCustomers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const usersQuery = useQuery({
    queryKey: ['master-data', 'users', activeCompanyId],
    queryFn: () => masterDataService.listUsers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['projects', activeCompanyId] })
    queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] })
  }

  const createProject = useMutation({
    mutationFn: () =>
      projectService.create({
        companyId: activeCompanyId as string,
        name: form.name.trim(),
        code: form.code.trim() || undefined,
        customerId: form.customerId || undefined,
        manager: form.manager || undefined,
        currencyCode: form.currencyCode || undefined,
        plannedStart: form.plannedStart || undefined,
        plannedEnd: form.plannedEnd || undefined,
        description: form.description.trim() || undefined,
      }),
    onSuccess: () => {
      invalidate()
      setForm({
        name: '',
        code: '',
        customerId: '',
        manager: '',
        currencyCode: 'HNL',
        plannedStart: '',
        plannedEnd: '',
        description: '',
      })
    },
  })

  const statusMutation = useMutation({
    mutationFn: ({ projectId, status }: { projectId: string; status: ProjectStatus }) =>
      projectService.transitionStatus(projectId, status),
    onSuccess: invalidate,
  })

  const columns: TableColumn<Project>[] = [
    { key: 'code', header: 'Código', render: (row) => row.code ?? '—' },
    {
      key: 'name',
      header: 'Proyecto',
      render: (row) => (
        <button className="nx-link-button" type="button" onClick={() => navigate(`/proyectos/${row.id}`)}>
          {row.name}
        </button>
      ),
    },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{statusLabel(row.status)}</Badge> },
    { key: 'manager', header: 'Responsable', render: (row) => row.manager ?? '—' },
    { key: 'dates', header: 'Plan', render: (row) => row.plannedStart && row.plannedEnd ? `${row.plannedStart} → ${row.plannedEnd}` : '—' },
    {
      key: 'selected',
      header: 'Contexto',
      render: (row) =>
        context.activeProjectId === row.id ? (
          <Badge tone="info">Seleccionado</Badge>
        ) : (
          <Button variant="secondary" onClick={() => setActiveProject(row.id)}>
            Seleccionar
          </Button>
        ),
    },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <div className="nx-treasury__actions">
          {(NEXT_STATUS[row.status] ?? []).map((action) => (
            <Button
              key={action.status}
              variant={action.status === 'CANCELLED' ? 'ghost' : 'secondary'}
              loading={statusMutation.isPending}
              onClick={() => {
                if (action.status === 'CANCELLED' && !window.confirm(`¿Cancelar ${row.name}? Esta acción quedará auditada.`)) return
                statusMutation.mutate({ projectId: row.id, status: action.status })
              }}
            >
              {action.label}
            </Button>
          ))}
        </div>
      ),
    },
  ]

  if (companiesLoading) return <LoadingState label="Cargando compañía…" />
  if (companiesError) return <ErrorState description="No se pudo cargar la compañía." onRetry={() => refetch()} />
  if (!activeCompanyId || !activeCompany) {
    return <EmptyState icon="project" title="Sin compañía" description="Configura una compañía antes de crear proyectos." />
  }

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <h1 className="nx-dashboard__title">Proyectos</h1>
          <p className="nx-field__hint">Empresa activa: {activeCompany.name}. “Seleccionado” es solo contexto de navegación; el estado empresarial se controla por separado.</p>
        </div>
      </header>

      <Card title="Nuevo proyecto">
        <Input label="Nombre" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
        <Input label="Código (opcional)" value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} />
        <Select label="Cliente" value={form.customerId} onChange={(event) => setForm({ ...form, customerId: event.target.value })}>
          <option value="">Sin cliente asignado todavía</option>
          {(customersQuery.data ?? []).map((customer) => (
            <option key={customer.id} value={customer.id}>{customer.legalName}</option>
          ))}
        </Select>
        <Select label="Responsable" value={form.manager} onChange={(event) => setForm({ ...form, manager: event.target.value })}>
          <option value="">Sin responsable asignado</option>
          {(usersQuery.data ?? []).map((user) => (
            <option key={user.id} value={user.fullName}>{user.fullName}</option>
          ))}
        </Select>
        <Select label="Moneda" value={form.currencyCode} onChange={(event) => setForm({ ...form, currencyCode: event.target.value })}>
          <option value="HNL">HNL — Lempira hondureño</option>
          <option value="USD">USD — Dólar estadounidense</option>
        </Select>
        <Input label="Inicio previsto" type="date" value={form.plannedStart} onChange={(event) => setForm({ ...form, plannedStart: event.target.value })} />
        <Input label="Final previsto" type="date" value={form.plannedEnd} onChange={(event) => setForm({ ...form, plannedEnd: event.target.value })} />
        <Textarea label="Descripción" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
        {createProject.isError ? <p className="nx-field__error" role="alert">{(createProject.error as Error).message}</p> : null}
        <Button
          disabled={!form.name.trim() || createProject.isPending || Boolean(form.plannedStart && form.plannedEnd && form.plannedEnd < form.plannedStart)}
          loading={createProject.isPending}
          onClick={() => createProject.mutate()}
        >
          Crear proyecto
        </Button>
      </Card>

      {projectsQuery.isLoading ? (
        <LoadingState label="Cargando proyectos…" />
      ) : projectsQuery.isError ? (
        <ErrorState description="No se pudieron cargar los proyectos." onRetry={() => projectsQuery.refetch()} />
      ) : (projectsQuery.data ?? []).length > 0 ? (
        <Table columns={columns} rows={projectsQuery.data ?? []} getRowKey={(row) => row.id} />
      ) : (
        <EmptyState icon="project" title="Sin proyectos" description="Crea el primer proyecto de esta compañía para empezar." />
      )}
    </div>
  )
}
