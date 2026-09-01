import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { crmService } from '../../services/crmService'
import { masterDataService } from '../../services/masterDataService'
import { projectService } from '../../services/projectService'
import type { Project, ProjectStatus } from '../../types/project'
import { statusLabel } from '../../utils/statusLabels'
import { useActiveContext } from '../context/useActiveContext'
import { ProjectWizard } from './ProjectWizard'

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
  const [wizardOpen, setWizardOpen] = useState(false)

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
  const costCentersQuery = useQuery({
    queryKey: ['master-data', 'cost-centers', activeCompanyId],
    queryFn: () => masterDataService.listCostCenters(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const projects = Array.isArray(projectsQuery.data) ? projectsQuery.data : []
  const customers = Array.isArray(customersQuery.data) ? customersQuery.data : []
  const users = Array.isArray(usersQuery.data) ? usersQuery.data : []
  const costCenters = Array.isArray(costCentersQuery.data) ? costCentersQuery.data : []

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['projects', activeCompanyId] })
    queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] })
  }

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
        <Button onClick={() => setWizardOpen((open) => !open)}>
          {wizardOpen ? 'Cerrar asistente' : 'Nuevo proyecto'}
        </Button>
      </header>

      {wizardOpen ? (
        <Card title="Nuevo proyecto — asistente guiado">
          <ProjectWizard
            companyId={activeCompanyId}
            customers={customers}
            users={users}
            costCenters={costCenters}
            onCreated={(project) => {
              invalidate()
              setWizardOpen(false)
              navigate(`/proyectos/${project.id}`)
            }}
          />
        </Card>
      ) : null}

      {projectsQuery.isLoading ? (
        <LoadingState label="Cargando proyectos…" />
      ) : projectsQuery.isError ? (
        <ErrorState description="No se pudieron cargar los proyectos." onRetry={() => projectsQuery.refetch()} />
      ) : projects.length > 0 ? (
        <Table columns={columns} rows={projects} getRowKey={(row) => row.id} />
      ) : (
        <EmptyState icon="project" title="Sin proyectos" description="Crea el primer proyecto de esta compañía para empezar." />
      )}
    </div>
  )
}
