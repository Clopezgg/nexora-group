import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, Card, EmptyState, ErrorState, Input, LoadingState, Modal, Select, Table, type TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { projectService } from '../../services/projectService'
import type { Milestone, ProjectTask } from '../../types/project'

export function PlanningPage() {
  const { activeCompanyId, isLoading: loadingCompany } = useActiveCompany()
  const [projectId, setProjectId] = useState('')
  const [taskOpen, setTaskOpen] = useState(false)
  const [milestoneOpen, setMilestoneOpen] = useState(false)
  const [task, setTask] = useState({ name: '', owner: '', plannedStart: '', plannedEnd: '', dependsOnTaskId: '' })
  const [milestone, setMilestone] = useState({ name: '', dueDate: '' })
  const client = useQueryClient()
  const projects = useQuery({ queryKey: ['projects', activeCompanyId], queryFn: () => projectService.list(activeCompanyId as string), enabled: Boolean(activeCompanyId) })
  const tasks = useQuery({ queryKey: ['projects', projectId, 'tasks'], queryFn: () => projectService.listTasks(projectId), enabled: Boolean(projectId) })
  const milestones = useQuery({ queryKey: ['projects', projectId, 'milestones'], queryFn: () => projectService.listMilestones(projectId), enabled: Boolean(projectId) })
  const createTask = useMutation({ mutationFn: () => projectService.createTask(projectId, { name: task.name, owner: task.owner || undefined, plannedStart: task.plannedStart || undefined, plannedEnd: task.plannedEnd || undefined, dependsOnTaskId: task.dependsOnTaskId || undefined }), onSuccess: () => { client.invalidateQueries({ queryKey: ['projects', projectId, 'tasks'] }); setTaskOpen(false); setTask({ name: '', owner: '', plannedStart: '', plannedEnd: '', dependsOnTaskId: '' }) } })
  const createMilestone = useMutation({ mutationFn: () => projectService.createMilestone(projectId, milestone), onSuccess: () => { client.invalidateQueries({ queryKey: ['projects', projectId, 'milestones'] }); setMilestoneOpen(false); setMilestone({ name: '', dueDate: '' }) } })

  if (loadingCompany) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) return <EmptyState title="Selecciona una compañía" description="La planificación se organiza por proyecto de una compañía activa." />

  const taskColumns: TableColumn<ProjectTask>[] = [
    { key: 'name', header: 'Tarea', render: (row) => row.name },
    { key: 'owner', header: 'Responsable', render: (row) => row.owner ?? '—' },
    { key: 'plannedStart', header: 'Inicio', render: (row) => row.plannedStart ?? '—' },
    { key: 'plannedEnd', header: 'Fin', render: (row) => row.plannedEnd ?? '—' },
    { key: 'dependsOnTaskId', header: 'Depende de', render: (row) => tasks.data?.find((candidate) => candidate.id === row.dependsOnTaskId)?.name ?? '—' },
  ]
  const milestoneColumns: TableColumn<Milestone>[] = [
    { key: 'name', header: 'Hito', render: (row) => row.name },
    { key: 'dueDate', header: 'Fecha objetivo', render: (row) => row.dueDate },
    { key: 'status', header: 'Estado', render: (row) => row.status },
  ]
  return <div>
    <header className="nx-page__header"><div><h1 className="nx-dashboard__title">Planeación</h1><p className="nx-field__hint">Tareas, hitos y dependencias del proyecto seleccionado.</p></div></header>
    <Card>
      {projects.isLoading ? <LoadingState label="Cargando proyectos…" /> : projects.isError ? <ErrorState onRetry={() => projects.refetch()} /> : <Select label="Proyecto" value={projectId} onChange={(event) => setProjectId(event.target.value)}><option value="">Selecciona un proyecto</option>{(projects.data ?? []).map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</Select>}
    </Card>
    {projectId ? <>
      <Card title="Tareas"><div className="nx-page__header"><span /><Button onClick={() => setTaskOpen(true)}>Nueva tarea</Button></div>{tasks.isLoading ? <LoadingState label="Cargando tareas…" /> : tasks.isError ? <ErrorState onRetry={() => tasks.refetch()} /> : <Table columns={taskColumns} rows={tasks.data ?? []} getRowKey={(row) => row.id} emptyMessage="Sin tareas registradas." />}</Card>
      <Card title="Hitos"><div className="nx-page__header"><span /><Button onClick={() => setMilestoneOpen(true)}>Nuevo hito</Button></div>{milestones.isLoading ? <LoadingState label="Cargando hitos…" /> : milestones.isError ? <ErrorState onRetry={() => milestones.refetch()} /> : <Table columns={milestoneColumns} rows={milestones.data ?? []} getRowKey={(row) => row.id} emptyMessage="Sin hitos registrados." />}</Card>
    </> : <EmptyState title="Selecciona un proyecto" description="Elige un proyecto para consultar o registrar su planeación." />}
    <Modal open={taskOpen} title="Nueva tarea" onClose={() => setTaskOpen(false)}><form onSubmit={(event) => { event.preventDefault(); createTask.mutate() }}><Input label="Nombre" value={task.name} onChange={(event) => setTask({ ...task, name: event.target.value })} required /><Input label="Responsable" value={task.owner} onChange={(event) => setTask({ ...task, owner: event.target.value })} /><Input label="Inicio planeado" type="date" value={task.plannedStart} onChange={(event) => setTask({ ...task, plannedStart: event.target.value })} /><Input label="Fin planeado" type="date" value={task.plannedEnd} onChange={(event) => setTask({ ...task, plannedEnd: event.target.value })} /><Select label="Depende de" value={task.dependsOnTaskId} onChange={(event) => setTask({ ...task, dependsOnTaskId: event.target.value })}><option value="">Sin dependencia</option>{(tasks.data ?? []).map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.name}</option>)}</Select>{createTask.isError ? <p className="nx-field__error">{(createTask.error as Error).message}</p> : null}<Button type="submit" loading={createTask.isPending}>Guardar tarea</Button></form></Modal>
    <Modal open={milestoneOpen} title="Nuevo hito" onClose={() => setMilestoneOpen(false)}><form onSubmit={(event) => { event.preventDefault(); createMilestone.mutate() }}><Input label="Nombre" value={milestone.name} onChange={(event) => setMilestone({ ...milestone, name: event.target.value })} required /><Input label="Fecha objetivo" type="date" value={milestone.dueDate} onChange={(event) => setMilestone({ ...milestone, dueDate: event.target.value })} required />{createMilestone.isError ? <p className="nx-field__error">{(createMilestone.error as Error).message}</p> : null}<Button type="submit" loading={createMilestone.isPending}>Guardar hito</Button></form></Modal>
  </div>
}
