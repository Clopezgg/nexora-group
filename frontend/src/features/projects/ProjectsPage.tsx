import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
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
import { crmService } from '../../services/crmService'
import { masterDataService } from '../../services/masterDataService'
import { projectService } from '../../services/projectService'
import type { Project, ProjectStatus } from '../../types/project'
import { PROJECT_STATUS_LABELS, projectStatusLabel } from '../../utils/statusLabels'
import { useActiveContext } from '../context/useActiveContext'
import { ProjectWizard } from './ProjectWizard'

// Sin motor de transiciones local (§9): las acciones de ciclo de vida viven en
// el Project Cockpit, que consume GET /projects/{id}/lifecycle. Aquí solo se
// abre el proyecto o se fija como contexto de navegación.

const FILTERABLE_STATUSES: ProjectStatus[] = [
  'PLANNING',
  'ACTIVE',
  'ON_HOLD',
  'COMPLETED',
  'CLOSED',
  'CANCELLED',
]

export function ProjectsPage() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { context, setActiveProject } = useActiveContext()
  const { activeCompany, activeCompanyId, isLoading: companiesLoading, isError: companiesError, refetch } = useActiveCompany()
  const [wizardOpen, setWizardOpen] = useState(false)
  const [filterStatus, setFilterStatus] = useState('')
  const [showArchived, setShowArchived] = useState(false)
  const [filterText, setFilterText] = useState('')

  const effectiveStatus = showArchived && !filterStatus ? '' : filterStatus
  const projectsQuery = useQuery({
    queryKey: ['projects', activeCompanyId, effectiveStatus || (showArchived ? 'ALL' : 'DEFAULT')],
    queryFn: () =>
      projectService.list(activeCompanyId as string, {
        status: effectiveStatus || undefined,
        includeArchived: showArchived,
      }),
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
    queryClient.invalidateQueries({ queryKey: ['projects'] })
    queryClient.invalidateQueries({ queryKey: ['dashboard', 'summary'] })
  }

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
    { key: 'status', header: 'Estado', render: (row) => <Badge>{projectStatusLabel(row.status)}</Badge> },
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
        <Button variant="secondary" onClick={() => navigate(`/proyectos/${row.id}`)}>
          Abrir
        </Button>
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
          <p className="nx-field__hint">Empresa activa: {activeCompany.name}. “Seleccionado” es solo contexto de navegación; el ciclo de vida del proyecto se administra desde su ficha.</p>
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

      <FilterBar
        onClear={() => {
          setFilterStatus('')
          setFilterText('')
          setShowArchived(false)
        }}
      >
        <Input
          label="Buscar proyecto"
          value={filterText}
          onChange={(event) => setFilterText(event.target.value)}
          placeholder="Nombre o código…"
        />
        <Select
          label="Estado"
          value={filterStatus}
          onChange={(event) => setFilterStatus(event.target.value)}
        >
          <option value="">Todos</option>
          {FILTERABLE_STATUSES.map((s) => (
            <option key={s} value={s}>
              {PROJECT_STATUS_LABELS[s]}
            </option>
          ))}
          <option value="ARCHIVED">Archivados</option>
        </Select>
        <label className="nx-field">
          <span className="nx-field__label">Archivados</span>
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(event) => setShowArchived(event.target.checked)}
          />{' '}
          Mostrar archivados
        </label>
      </FilterBar>

      {projectsQuery.isLoading ? (
        <LoadingState label="Cargando proyectos…" />
      ) : projectsQuery.isError ? (
        <ErrorState description="No se pudieron cargar los proyectos." onRetry={() => projectsQuery.refetch()} />
      ) : projects.length > 0 ? (
        <Table
          columns={columns}
          rows={projects.filter(
            (row) =>
              !filterText ||
              row.name.toLowerCase().includes(filterText.toLowerCase()) ||
              (row.code ?? '').toLowerCase().includes(filterText.toLowerCase()),
          )}
          getRowKey={(row) => row.id}
        />
      ) : (
        <EmptyState icon="project" title="Sin proyectos" description="No hay proyectos que coincidan con el filtro." />
      )}
    </div>
  )
}
