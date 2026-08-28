import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, EmptyState, ErrorState, Input, LoadingState, Select, Table, Textarea } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { documentService } from '../../services/documentService'
import { masterDataService } from '../../services/masterDataService'
import { projectService } from '../../services/projectService'
import type { ProgressRecord } from '../../types/project'
import { RequiresActiveProject } from './RequiresActiveProject'

const EMPTY_FORM = { recordDate: '', plannedPercent: '', actualPercent: '', wbsNodeId: '', description: '', responsible: '', evidenceId: '' }

function ProgressList({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient()
  const { activeCompanyId } = useActiveCompany()
  const [form, setForm] = useState(EMPTY_FORM)

  const progressQuery = useQuery({ queryKey: ['progress', projectId], queryFn: () => projectService.listProgress(projectId) })
  const wbsQuery = useQuery({ queryKey: ['wbs', projectId], queryFn: () => projectService.listWbs(projectId) })
  const usersQuery = useQuery({
    queryKey: ['master-data', 'users', activeCompanyId],
    queryFn: () => masterDataService.listUsers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const evidenceQuery = useQuery({
    queryKey: ['evidence', activeCompanyId],
    queryFn: () => documentService.listEvidence(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const createProgress = useMutation({
    mutationFn: () => projectService.createProgress(projectId, {
      recordDate: form.recordDate,
      plannedPercent: Number(form.plannedPercent),
      actualPercent: Number(form.actualPercent),
      wbsNodeId: form.wbsNodeId || null,
      description: form.description.trim() || undefined,
      responsible: form.responsible || undefined,
      evidenceId: form.evidenceId || null,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['progress', projectId] })
      queryClient.invalidateQueries({ queryKey: ['forecast', projectId] })
      queryClient.invalidateQueries({ queryKey: ['project', projectId, 'financial-summary'] })
      setForm(EMPTY_FORM)
    },
  })

  const wbsById = useMemo(() => new Map((wbsQuery.data ?? []).map((node) => [node.id, `${node.code} · ${node.name}`])), [wbsQuery.data])
  const evidenceById = useMemo(() => new Map((evidenceQuery.data ?? []).map((item) => [item.id, item.originalFilename])), [evidenceQuery.data])
  const columns: TableColumn<ProgressRecord>[] = [
    { key: 'date', header: 'Fecha', render: (row) => row.recordDate },
    { key: 'wbs', header: 'WBS', render: (row) => row.wbsNodeId ? (wbsById.get(row.wbsNodeId) ?? 'WBS no disponible') : 'Proyecto general' },
    { key: 'planned', header: 'Planeado', render: (row) => `${Number(row.plannedPercent).toFixed(1)}%` },
    { key: 'actual', header: 'Real', render: (row) => `${Number(row.actualPercent).toFixed(1)}%` },
    { key: 'responsible', header: 'Responsable', render: (row) => row.responsible ?? '—' },
    { key: 'description', header: 'Descripción', render: (row) => row.description ?? '—' },
    { key: 'evidence', header: 'Evidencia', render: (row) => row.evidenceId ? (evidenceById.get(row.evidenceId) ?? 'Evidencia vinculada') : '—' },
  ]

  if (progressQuery.isLoading) return <LoadingState label="Cargando avances…" />
  if (progressQuery.isError) return <ErrorState description="No se pudieron cargar los avances." onRetry={() => progressQuery.refetch()} />

  const planned = Number(form.plannedPercent)
  const actual = Number(form.actualPercent)
  const percentagesValid = form.plannedPercent !== '' && form.actualPercent !== '' && planned >= 0 && planned <= 100 && actual >= 0 && actual <= 100

  return <>
    <Card title="Registrar avance">
      <Select label="WBS / alcance del avance" value={form.wbsNodeId} onChange={(event) => setForm({ ...form, wbsNodeId: event.target.value })}>
        <option value="">Proyecto general</option>
        {(wbsQuery.data ?? []).map((node) => <option key={node.id} value={node.id}>{'—'.repeat(node.level)} {node.code} · {node.name}</option>)}
      </Select>
      <Input label="Fecha" type="date" value={form.recordDate} onChange={(event) => setForm({ ...form, recordDate: event.target.value })} />
      <Input label="Planeado (%)" type="number" min="0" max="100" step="0.01" value={form.plannedPercent} onChange={(event) => setForm({ ...form, plannedPercent: event.target.value })} />
      <Input label="Real (%)" type="number" min="0" max="100" step="0.01" value={form.actualPercent} onChange={(event) => setForm({ ...form, actualPercent: event.target.value })} />
      <Select label="Responsable" value={form.responsible} onChange={(event) => setForm({ ...form, responsible: event.target.value })}>
        <option value="">Sin responsable especificado</option>
        {(usersQuery.data ?? []).map((user) => <option key={user.id} value={user.fullName}>{user.fullName}</option>)}
      </Select>
      <Textarea label="Descripción del avance" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
      <Select label="Evidencia" value={form.evidenceId} onChange={(event) => setForm({ ...form, evidenceId: event.target.value })}>
        <option value="">Sin evidencia</option>
        {(evidenceQuery.data ?? []).map((item) => <option key={item.id} value={item.id}>{item.originalFilename}</option>)}
      </Select>
      <p className="nx-field__hint">Las evidencias se cargan en Control → Evidencias y aquí se vinculan por su ID real; el backend valida que pertenezcan a la misma compañía.</p>
      <Button disabled={!form.recordDate || !percentagesValid || createProgress.isPending} loading={createProgress.isPending} onClick={() => createProgress.mutate()}>Registrar avance</Button>
      {createProgress.isError ? <p className="nx-field__error" role="alert">{(createProgress.error as Error).message}</p> : null}
    </Card>

    {(progressQuery.data ?? []).length > 0 ? <Table columns={columns} rows={progressQuery.data ?? []} getRowKey={(row) => row.id} /> : <EmptyState icon="chart" title="Sin avances" description="Registra el primer avance físico del proyecto." />}
  </>
}

export function ProgressPage() {
  return <div><h1 className="nx-dashboard__title">Avances</h1><RequiresActiveProject>{(projectId) => <ProgressList projectId={projectId} />}</RequiresActiveProject></div>
}
