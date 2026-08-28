import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, MoneyInput, Select, Table, Textarea } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { masterDataService } from '../../services/masterDataService'
import { projectService } from '../../services/projectService'
import type { ChangeOrder } from '../../types/project'
import { formatMoney } from '../../utils/currency'
import { statusLabel } from '../../utils/statusLabels'
import { RequiresActiveProject } from './RequiresActiveProject'

const STATUS_TONE: Record<ChangeOrder['status'], 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = {
  DRAFT: 'neutral', SUBMITTED: 'info', APPROVED: 'success', REJECTED: 'danger', IMPLEMENTED: 'success', CANCELLED: 'danger',
}

const EMPTY_FORM = { reason: '', wbsNodeId: '', scopeChange: '', costImpact: null as number | null, contractImpact: null as number | null, scheduleDays: '' }

function ChangeOrdersList({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient()
  const { activeCompanyId } = useActiveCompany()
  const [form, setForm] = useState(EMPTY_FORM)
  const changeOrdersQuery = useQuery({ queryKey: ['change-orders', projectId], queryFn: () => projectService.listChangeOrders(projectId) })
  const wbsQuery = useQuery({ queryKey: ['wbs', projectId], queryFn: () => projectService.listWbs(projectId) })
  const usersQuery = useQuery({ queryKey: ['master-data', 'users', activeCompanyId], queryFn: () => masterDataService.listUsers(activeCompanyId as string), enabled: Boolean(activeCompanyId) })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['change-orders', projectId] })
    queryClient.invalidateQueries({ queryKey: ['budget-summary', projectId] })
    queryClient.invalidateQueries({ queryKey: ['budget-active', projectId] })
    queryClient.invalidateQueries({ queryKey: ['forecast', projectId] })
    queryClient.invalidateQueries({ queryKey: ['project', projectId, 'financial-summary'] })
  }

  const createChangeOrder = useMutation({
    mutationFn: () => projectService.createChangeOrder(projectId, {
      reason: form.reason.trim(),
      wbsNodeId: form.wbsNodeId || null,
      scopeChange: form.scopeChange.trim() || undefined,
      budgetChangeAmount: form.costImpact ?? 0,
      contractChangeAmount: form.contractImpact ?? 0,
      scheduleChangeDays: form.scheduleDays === '' ? null : Number(form.scheduleDays),
    }),
    onSuccess: () => { invalidate(); setForm(EMPTY_FORM) },
  })
  const submitChangeOrder = useMutation({ mutationFn: (id: string) => projectService.submitChangeOrder(id), onSuccess: invalidate })
  const approveChangeOrder = useMutation({ mutationFn: (id: string) => projectService.approveChangeOrder(id), onSuccess: invalidate })

  const wbsById = useMemo(() => new Map((wbsQuery.data ?? []).map((node) => [node.id, `${node.code} · ${node.name}`])), [wbsQuery.data])
  const userById = useMemo(() => new Map((usersQuery.data ?? []).map((user) => [user.id, user.fullName])), [usersQuery.data])
  const columns: TableColumn<ChangeOrder>[] = [
    { key: 'reason', header: 'Motivo', render: (row) => row.reason },
    { key: 'wbs', header: 'WBS', render: (row) => row.wbsNodeId ? (wbsById.get(row.wbsNodeId) ?? 'WBS no disponible') : 'Proyecto general' },
    { key: 'scope', header: 'Cambio de alcance', render: (row) => row.scopeChange ?? '—' },
    { key: 'cost', header: 'Impacto en costo', render: (row) => formatMoney(Number(row.budgetChangeAmount), 'HNL') },
    { key: 'contract', header: 'Impacto contractual', render: (row) => formatMoney(Number(row.contractChangeAmount), 'HNL') },
    { key: 'schedule', header: 'Calendario', render: (row) => row.scheduleChangeDays === null ? '—' : `${row.scheduleChangeDays >= 0 ? '+' : ''}${row.scheduleChangeDays} día(s)` },
    { key: 'requested', header: 'Solicitado por', render: (row) => userById.get(row.requestedBy) ?? row.requestedBy.slice(0, 8) },
    { key: 'approved', header: 'Aprobado por', render: (row) => row.approvedBy ? (userById.get(row.approvedBy) ?? row.approvedBy.slice(0, 8)) : '—' },
    { key: 'status', header: 'Estado', render: (row) => <Badge tone={STATUS_TONE[row.status]}>{statusLabel(row.status)}</Badge> },
    { key: 'actions', header: 'Acciones', render: (row) => <div className="nx-treasury__actions">
      {row.status === 'DRAFT' ? <Button variant="secondary" loading={submitChangeOrder.isPending} onClick={() => submitChangeOrder.mutate(row.id)}>Enviar a aprobación</Button> : null}
      {row.status === 'SUBMITTED' ? <Button variant="secondary" loading={approveChangeOrder.isPending} onClick={() => approveChangeOrder.mutate(row.id)}>Aprobar</Button> : null}
    </div> },
  ]

  if (changeOrdersQuery.isLoading) return <LoadingState label="Cargando órdenes de cambio…" />
  if (changeOrdersQuery.isError) return <ErrorState description="No se pudieron cargar las órdenes de cambio." onRetry={() => changeOrdersQuery.refetch()} />

  return <>
    <Card title="Nueva orden de cambio">
      <Select label="WBS afectado" value={form.wbsNodeId} onChange={(event) => setForm({ ...form, wbsNodeId: event.target.value })}>
        <option value="">Proyecto general</option>
        {(wbsQuery.data ?? []).map((node) => <option key={node.id} value={node.id}>{'—'.repeat(node.level)} {node.code} · {node.name}</option>)}
      </Select>
      <Textarea label="Motivo" value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} required />
      <Textarea label="Descripción del cambio de alcance" value={form.scopeChange} onChange={(event) => setForm({ ...form, scopeChange: event.target.value })} />
      <MoneyInput label="Impacto en COSTO interno (+/- HNL)" value={form.costImpact} onChange={(value) => setForm({ ...form, costImpact: value })} />
      <MoneyInput label="Impacto CONTRACTUAL al cliente (+/- HNL)" value={form.contractImpact} onChange={(value) => setForm({ ...form, contractImpact: value })} />
      <p className="nx-field__hint">El impacto contractual se documenta por separado y no modifica silenciosamente el Contrato de venta. El impacto en costo es el único que revisa el Budget del proyecto al aprobarse.</p>
      <Input label="Impacto en calendario (días, +/-)" type="number" step="1" value={form.scheduleDays} onChange={(event) => setForm({ ...form, scheduleDays: event.target.value })} />
      <Button disabled={!form.reason.trim() || createChangeOrder.isPending} loading={createChangeOrder.isPending} onClick={() => createChangeOrder.mutate()}>Crear borrador</Button>
      {createChangeOrder.isError ? <p className="nx-field__error" role="alert">{(createChangeOrder.error as Error).message}</p> : null}
    </Card>
    {(submitChangeOrder.isError || approveChangeOrder.isError) ? <p className="nx-field__error" role="alert">{((submitChangeOrder.error ?? approveChangeOrder.error) as Error).message}</p> : null}
    {(changeOrdersQuery.data ?? []).length > 0 ? <Table columns={columns} rows={changeOrdersQuery.data ?? []} getRowKey={(row) => row.id} /> : <EmptyState icon="inbox" title="Sin órdenes de cambio" description="Registra el primer cambio de alcance, costo o calendario del proyecto." />}
  </>
}

export function ChangeOrdersPage() {
  return <div><h1 className="nx-dashboard__title">Órdenes de cambio</h1><RequiresActiveProject>{(projectId) => <ChangeOrdersList projectId={projectId} />}</RequiresActiveProject></div>
}
