import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Card, EmptyState, ErrorState, LoadingState, MoneyInput, Table, Textarea } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { projectService } from '../../services/projectService'
import type { ChangeOrder } from '../../types/project'
import { RequiresActiveProject } from './RequiresActiveProject'

const STATUS_TONE: Record<ChangeOrder['status'], 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = {
  DRAFT: 'neutral',
  SUBMITTED: 'info',
  APPROVED: 'success',
  REJECTED: 'danger',
  IMPLEMENTED: 'success',
  CANCELLED: 'danger',
}

function ChangeOrdersList({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')
  const [amount, setAmount] = useState<number | null>(null)

  const changeOrdersQuery = useQuery({
    queryKey: ['change-orders', projectId],
    queryFn: () => projectService.listChangeOrders(projectId),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['change-orders', projectId] })
    queryClient.invalidateQueries({ queryKey: ['budget-summary', projectId] })
    queryClient.invalidateQueries({ queryKey: ['budget-active', projectId] })
    queryClient.invalidateQueries({ queryKey: ['forecast', projectId] })
  }

  const createChangeOrder = useMutation({
    mutationFn: () => projectService.createChangeOrder(projectId, { reason, budgetChangeAmount: amount ?? 0 }),
    onSuccess: () => {
      invalidate()
      setReason('')
      setAmount(null)
    },
  })
  const submitChangeOrder = useMutation({
    mutationFn: (id: string) => projectService.submitChangeOrder(id),
    onSuccess: invalidate,
  })
  const approveChangeOrder = useMutation({
    mutationFn: (id: string) => projectService.approveChangeOrder(id),
    onSuccess: invalidate,
  })

  if (changeOrdersQuery.isLoading) return <LoadingState label="Cargando órdenes de cambio…" />
  if (changeOrdersQuery.isError) {
    return <ErrorState description="No se pudieron cargar las órdenes de cambio." onRetry={() => changeOrdersQuery.refetch()} />
  }

  const columns: TableColumn<ChangeOrder>[] = [
    { key: 'reason', header: 'Motivo', render: (row) => row.reason },
    { key: 'amount', header: 'Impacto presupuestal', render: (row) => row.budgetChangeAmount },
    { key: 'status', header: 'Estado', render: (row) => <Badge tone={STATUS_TONE[row.status]}>{row.status}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <>
          {row.status === 'DRAFT' ? (
            <Button variant="secondary" loading={submitChangeOrder.isPending} onClick={() => submitChangeOrder.mutate(row.id)}>
              Enviar a aprobación
            </Button>
          ) : null}
          {row.status === 'SUBMITTED' ? (
            <Button loading={approveChangeOrder.isPending} onClick={() => approveChangeOrder.mutate(row.id)}>
              Aprobar
            </Button>
          ) : null}
        </>
      ),
    },
  ]

  const orders = changeOrdersQuery.data ?? []

  return (
    <div>
      <Card title="Nueva orden de cambio">
        <Textarea label="Motivo" value={reason} onChange={(event) => setReason(event.target.value)} />
        <MoneyInput label="Impacto presupuestal (+/-)" value={amount} onChange={setAmount} />
        <Button disabled={!reason || createChangeOrder.isPending} loading={createChangeOrder.isPending} onClick={() => createChangeOrder.mutate()}>
          Crear orden de cambio
        </Button>
      </Card>

      {orders.length === 0 ? (
        <EmptyState icon="🔀" title="Sin órdenes de cambio" description="Todavía no se ha solicitado ningún cambio de alcance/presupuesto." />
      ) : (
        <Table columns={columns} rows={orders} getRowKey={(row) => row.id} />
      )}
    </div>
  )
}

export function ChangeOrdersPage() {
  return (
    <div>
      <h1 className="nx-dashboard__title">Órdenes de cambio</h1>
      <RequiresActiveProject>{(projectId) => <ChangeOrdersList projectId={projectId} />}</RequiresActiveProject>
    </div>
  )
}
