import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, EmptyState, ErrorState, Input, LoadingState, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { companyService, projectService } from '../../services/projectService'
import type { Project } from '../../types/project'
import { useActiveContext } from '../context/useActiveContext'

export function ProjectsPage() {
  const queryClient = useQueryClient()
  const { context, setActiveProject } = useActiveContext()
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null)
  const [newCompanyName, setNewCompanyName] = useState('')
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectCode, setNewProjectCode] = useState('')

  const companiesQuery = useQuery({
    queryKey: ['companies'],
    queryFn: companyService.list,
  })

  const activeCompanyId = selectedCompanyId ?? companiesQuery.data?.[0]?.id ?? null

  const projectsQuery = useQuery({
    queryKey: ['projects', activeCompanyId],
    queryFn: () => projectService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const createCompany = useMutation({
    mutationFn: () => companyService.create(newCompanyName, 'HNL'),
    onSuccess: (company) => {
      queryClient.invalidateQueries({ queryKey: ['companies'] })
      setSelectedCompanyId(company.id)
      setNewCompanyName('')
    },
  })

  const createProject = useMutation({
    mutationFn: () =>
      projectService.create({ companyId: activeCompanyId as string, name: newProjectName, code: newProjectCode || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', activeCompanyId] })
      setNewProjectName('')
      setNewProjectCode('')
    },
  })

  const columns: TableColumn<Project>[] = [
    { key: 'code', header: 'Código', render: (row) => row.code ?? '—' },
    { key: 'name', header: 'Nombre', render: (row) => row.name },
    { key: 'status', header: 'Estado', render: (row) => row.status },
    {
      key: 'active',
      header: 'Proyecto activo',
      render: (row) =>
        context.activeProjectId === row.id ? (
          <span aria-label="Proyecto activo">Activo</span>
        ) : (
          <Button variant="secondary" onClick={() => setActiveProject(row.id)}>
            Usar como activo
          </Button>
        ),
    },
  ]

  if (companiesQuery.isLoading) return <LoadingState label="Cargando compañías…" />
  if (companiesQuery.isError) {
    return (
      <ErrorState
        description="No se pudieron cargar las compañías."
        onRetry={() => companiesQuery.refetch()}
      />
    )
  }

  return (
    <div>
      <h1 className="nx-dashboard__title">Proyectos</h1>

      {companiesQuery.data && companiesQuery.data.length > 0 ? (
        <Card title="Compañía">
          <select
            className="nx-input"
            value={activeCompanyId ?? ''}
            onChange={(event) => setSelectedCompanyId(event.target.value)}
            aria-label="Seleccionar compañía"
          >
            {companiesQuery.data.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
        </Card>
      ) : (
        <Card title="Crea tu primera compañía">
          <Input
            name="companyName"
            label="Nombre de la compañía"
            value={newCompanyName}
            onChange={(event) => setNewCompanyName(event.target.value)}
          />
          <Button
            disabled={!newCompanyName || createCompany.isPending}
            loading={createCompany.isPending}
            onClick={() => createCompany.mutate()}
          >
            Crear compañía
          </Button>
        </Card>
      )}

      {activeCompanyId ? (
        <>
          <Card title="Nuevo proyecto">
            <Input
              name="projectName"
              label="Nombre"
              value={newProjectName}
              onChange={(event) => setNewProjectName(event.target.value)}
            />
            <Input
              name="projectCode"
              label="Código (opcional)"
              value={newProjectCode}
              onChange={(event) => setNewProjectCode(event.target.value)}
            />
            <Button
              disabled={!newProjectName || createProject.isPending}
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
          ) : projectsQuery.data && projectsQuery.data.length > 0 ? (
            <Table
              columns={columns}
              rows={projectsQuery.data}
              getRowKey={(row) => row.id}
              emptyMessage="Sin proyectos todavía."
            />
          ) : (
            <EmptyState
              icon="project"
              title="Sin proyectos"
              description="Crea el primer proyecto de esta compañía para empezar."
            />
          )}
        </>
      ) : null}
    </div>
  )
}
