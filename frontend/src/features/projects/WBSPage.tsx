import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
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
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { masterDataService } from '../../services/masterDataService'
import { projectService, type WBSInput } from '../../services/projectService'
import type { WBSFinancialSummary, WBSNode, WBSStatus } from '../../types/project'
import { formatMoney } from '../../utils/currency'
import { statusLabel } from '../../utils/statusLabels'
import { RequiresActiveProject } from './RequiresActiveProject'

const EMPTY_FORM = { code: '', name: '', parentId: '', manager: '', plannedStart: '', plannedFinish: '' }
const WBS_STATUSES: WBSStatus[] = ['PLANNING', 'ACTIVE', 'ON_HOLD', 'COMPLETED', 'CANCELLED']

function flattenTree(nodes: WBSNode[]): WBSNode[] {
  const children = new Map<string | null, WBSNode[]>()
  for (const node of nodes) {
    const key = node.parentId ?? null
    children.set(key, [...(children.get(key) ?? []), node])
  }
  for (const group of children.values()) group.sort((a, b) => a.code.localeCompare(b.code))
  const result: WBSNode[] = []
  const visit = (parentId: string | null) => {
    for (const node of children.get(parentId) ?? []) {
      result.push(node)
      visit(node.id)
    }
  }
  visit(null)
  return result
}

function metric(value: string | null, currency = 'HNL') {
  return value === null ? '—' : formatMoney(Number(value), currency)
}

function WBSManager({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient()
  const { activeCompanyId } = useActiveCompany()
  const [form, setForm] = useState(EMPTY_FORM)
  const [editing, setEditing] = useState<WBSNode | null>(null)
  const [editForm, setEditForm] = useState<WBSInput>({})

  const wbsQuery = useQuery({ queryKey: ['wbs', projectId], queryFn: () => projectService.listWbs(projectId) })
  const financialQuery = useQuery({ queryKey: ['wbs', projectId, 'financial-summary'], queryFn: () => projectService.listWbsFinancials(projectId) })
  const usersQuery = useQuery({
    queryKey: ['master-data', 'users', activeCompanyId],
    queryFn: () => masterDataService.listUsers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['wbs', projectId] })
    queryClient.invalidateQueries({ queryKey: ['budget-active', projectId] })
    queryClient.invalidateQueries({ queryKey: ['project', projectId, 'financial-summary'] })
  }

  const createMutation = useMutation({
    mutationFn: () => projectService.createWbs(projectId, {
      code: form.code.trim(), name: form.name.trim(), parentId: form.parentId || null,
      manager: form.manager || null, plannedStart: form.plannedStart || null,
      plannedFinish: form.plannedFinish || null,
    }),
    onSuccess: () => { invalidate(); setForm(EMPTY_FORM) },
  })
  const updateMutation = useMutation({
    mutationFn: () => projectService.updateWbs(projectId, editing!.id, editForm),
    onSuccess: () => { invalidate(); setEditing(null); setEditForm({}) },
  })

  const nodes = useMemo(() => flattenTree(wbsQuery.data ?? []), [wbsQuery.data])
  const financialByNode = useMemo(
    () => new Map<string, WBSFinancialSummary>((financialQuery.data ?? []).map((row) => [row.wbsNodeId, row])),
    [financialQuery.data],
  )

  const beginEdit = (node: WBSNode) => {
    setEditing(node)
    setEditForm({
      code: node.code, name: node.name, parentId: node.parentId, manager: node.manager,
      plannedStart: node.plannedStart, plannedFinish: node.plannedFinish,
      status: node.status, progressPercent: Number(node.progressPercent),
    })
  }

  const columns: TableColumn<WBSNode>[] = [
    { key: 'name', header: 'WBS', render: (row) => <span style={{ paddingLeft: `${row.level * 20}px` }}>{row.level > 0 ? '↳ ' : ''}<strong>{row.code}</strong> · {row.name}</span> },
    { key: 'manager', header: 'Responsable', render: (row) => row.manager ?? '—' },
    { key: 'dates', header: 'Plan', render: (row) => row.plannedStart || row.plannedFinish ? `${row.plannedStart ?? '—'} → ${row.plannedFinish ?? '—'}` : '—' },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{statusLabel(row.status)}</Badge> },
    { key: 'progress', header: 'Avance', render: (row) => `${Number(row.progressPercent).toFixed(1)}%` },
    { key: 'budget', header: 'Presupuesto', render: (row) => metric(financialByNode.get(row.id)?.authorized ?? '0') },
    { key: 'committed', header: 'Comprometido', render: (row) => metric(financialByNode.get(row.id)?.committed ?? null) },
    { key: 'actual', header: 'Costo real', render: (row) => metric(financialByNode.get(row.id)?.actualCost ?? null) },
    { key: 'variance', header: 'Variación', render: (row) => metric(financialByNode.get(row.id)?.variance ?? null) },
    { key: 'actions', header: '', render: (row) => <Button variant="secondary" onClick={() => beginEdit(row)}>Editar</Button> },
  ]

  if (wbsQuery.isLoading) return <LoadingState label="Cargando WBS…" />
  if (wbsQuery.isError) return <ErrorState description="No se pudo cargar la WBS." onRetry={() => wbsQuery.refetch()} />

  return <>
    <Card title="Nuevo nodo WBS">
      <Input label="Código" value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} required />
      <Input label="Nombre" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
      <Select label="Nodo padre" value={form.parentId} onChange={(event) => setForm({ ...form, parentId: event.target.value })}>
        <option value="">Sin padre — nivel raíz</option>
        {nodes.map((node) => <option key={node.id} value={node.id}>{'—'.repeat(node.level)} {node.code} · {node.name}</option>)}
      </Select>
      <Select label="Responsable" value={form.manager} onChange={(event) => setForm({ ...form, manager: event.target.value })}>
        <option value="">Sin responsable</option>
        {(usersQuery.data ?? []).map((user) => <option key={user.id} value={user.fullName}>{user.fullName}</option>)}
      </Select>
      <Input label="Inicio previsto" type="date" value={form.plannedStart} onChange={(event) => setForm({ ...form, plannedStart: event.target.value })} />
      <Input label="Fin previsto" type="date" value={form.plannedFinish} onChange={(event) => setForm({ ...form, plannedFinish: event.target.value })} />
      <Button loading={createMutation.isPending} disabled={!form.code.trim() || !form.name.trim() || Boolean(form.plannedStart && form.plannedFinish && form.plannedFinish < form.plannedStart)} onClick={() => createMutation.mutate()}>Crear nodo</Button>
      {createMutation.isError ? <p className="nx-field__error" role="alert">{(createMutation.error as Error).message}</p> : null}
    </Card>

    {editing ? <Card title={`Editar WBS · ${editing.code}`}>
      <Input label="Código" value={String(editForm.code ?? '')} onChange={(event) => setEditForm({ ...editForm, code: event.target.value })} />
      <Input label="Nombre" value={String(editForm.name ?? '')} onChange={(event) => setEditForm({ ...editForm, name: event.target.value })} />
      <Select label="Nodo padre" value={editForm.parentId ?? ''} onChange={(event) => setEditForm({ ...editForm, parentId: event.target.value || null })}>
        <option value="">Sin padre — nivel raíz</option>
        {nodes.filter((node) => node.id !== editing.id).map((node) => <option key={node.id} value={node.id}>{'—'.repeat(node.level)} {node.code} · {node.name}</option>)}
      </Select>
      <Select label="Responsable" value={editForm.manager ?? ''} onChange={(event) => setEditForm({ ...editForm, manager: event.target.value || null })}>
        <option value="">Sin responsable</option>
        {(usersQuery.data ?? []).map((user) => <option key={user.id} value={user.fullName}>{user.fullName}</option>)}
      </Select>
      <Input label="Inicio previsto" type="date" value={editForm.plannedStart ?? ''} onChange={(event) => setEditForm({ ...editForm, plannedStart: event.target.value || null })} />
      <Input label="Fin previsto" type="date" value={editForm.plannedFinish ?? ''} onChange={(event) => setEditForm({ ...editForm, plannedFinish: event.target.value || null })} />
      <Select label="Estado" value={editForm.status ?? editing.status} onChange={(event) => setEditForm({ ...editForm, status: event.target.value as WBSStatus })}>
        {WBS_STATUSES.map((value) => <option key={value} value={value}>{statusLabel(value)}</option>)}
      </Select>
      <Input label="Avance físico (%)" type="number" min="0" max="100" step="0.01" value={editForm.progressPercent ?? 0} onChange={(event) => setEditForm({ ...editForm, progressPercent: Number(event.target.value) })} />
      <div className="nx-treasury__actions"><Button loading={updateMutation.isPending} onClick={() => updateMutation.mutate()}>Guardar cambios</Button><Button variant="ghost" onClick={() => { setEditing(null); setEditForm({}) }}>Cancelar</Button></div>
      {updateMutation.isError ? <p className="nx-field__error" role="alert">{(updateMutation.error as Error).message}</p> : null}
    </Card> : null}

    <Card title="Estructura WBS">
      {nodes.length === 0 ? <EmptyState icon="project" title="Sin WBS todavía" description="Crea la estructura de trabajo antes de congelar el presupuesto de costos." /> : <Table columns={columns} rows={nodes} getRowKey={(row) => row.id} />}
      <p className="nx-field__hint">Comprometido, costo real y variación muestran “—” mientras los documentos fuente no tengan atribución WBS autoritativa; NEXORA no inventa una distribución.</p>
    </Card>
  </>
}

export function WBSPage() {
  return <div><h1 className="nx-dashboard__title">WBS</h1><RequiresActiveProject>{(projectId) => <WBSManager projectId={projectId} />}</RequiresActiveProject></div>
}
