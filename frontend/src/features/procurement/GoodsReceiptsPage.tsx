import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Table,
  WarehouseSelector,
} from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { inventoryService } from '../../services/inventoryService'
import { procurementService } from '../../services/procurementService'
import type { PurchaseOrder } from '../../types/procurement'

const RECEIVABLE_STATUSES = ['SENT', 'APPROVED', 'PARTIALLY_RECEIVED']

export function GoodsReceiptsPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const handleMutationError = useMutationError()
  const [selectedPoId, setSelectedPoId] = useState<string | null>(null)
  const [warehouseId, setWarehouseId] = useState<string | null>(null)
  const [receivedAt, setReceivedAt] = useState(() => new Date().toISOString().slice(0, 10))
  const queryClient = useQueryClient()

  const ordersQuery = useQuery({
    queryKey: ['procurement', 'purchase-orders', activeCompanyId],
    queryFn: () => procurementService.listPurchaseOrders(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const warehousesQuery = useQuery({
    queryKey: ['inventory', 'warehouses', activeCompanyId],
    queryFn: () => inventoryService.listWarehouses(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const receivableOrders = (ordersQuery.data ?? []).filter((po) => RECEIVABLE_STATUSES.includes(po.status))
  const selectedOrder = receivableOrders.find((po) => po.id === selectedPoId) ?? null

  const [quantities, setQuantities] = useState<Record<string, string>>({})

  const receiveMutation = useMutation({
    mutationFn: () =>
      procurementService.createGoodsReceipt({
        purchaseOrderId: selectedOrder!.id,
        warehouseId: warehouseId as string,
        receivedAt,
        lines: selectedOrder!.lines
          .filter((line) => quantities[line.id])
          .map((line) => ({ purchaseOrderLineId: line.id, quantityReceived: quantities[line.id] })),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'purchase-orders', activeCompanyId] })
      setQuantities({})
    },
    onError: (error) => handleMutationError(error, 'Registrar recepción'),
  })

  const columns: TableColumn<PurchaseOrder>[] = [
    { key: 'number', header: 'Orden', render: (row) => row.poNumber },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{row.status}</Badge> },
    {
      key: 'select',
      header: '',
      render: (row) => (
        <Button variant="secondary" onClick={() => setSelectedPoId(row.id)}>
          Recibir
        </Button>
      ),
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return <EmptyState title="Configura una compañía primero" description="No hay compañías registradas todavía." />
  }

  const warehouseOptions = (warehousesQuery.data ?? []).map((w) => ({ id: w.id, label: `${w.code} — ${w.name}` }))

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Recepciones de mercadería</h1>
      </header>

      <Card title="Órdenes pendientes de recibir">
        {ordersQuery.isLoading ? (
          <LoadingState label="Cargando órdenes…" />
        ) : ordersQuery.isError ? (
          <ErrorState onRetry={() => ordersQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={receivableOrders}
            getRowKey={(row) => row.id}
            emptyMessage="No hay órdenes de compra enviadas pendientes de recepción."
          />
        )}
      </Card>

      {selectedOrder ? (
        <Card title={`Registrar recepción — ${selectedOrder.poNumber}`}>
          <WarehouseSelector options={warehouseOptions} value={warehouseId} onChange={setWarehouseId} />
          <Input
            label="Fecha de recepción"
            type="date"
            value={receivedAt}
            onChange={(e) => setReceivedAt(e.target.value)}
          />
          {selectedOrder.lines.map((line) => {
            const pending = Number(line.quantity) - Number(line.quantityReceived)
            return (
              <div key={line.id} className="nx-field">
                <label className="nx-field__label">
                  {line.description} (pendiente: {pending})
                </label>
                <Input
                  value={quantities[line.id] ?? ''}
                  onChange={(e) => setQuantities((prev) => ({ ...prev, [line.id]: e.target.value }))}
                  placeholder="Cantidad recibida"
                />
              </div>
            )
          })}
          <Button
            onClick={() => receiveMutation.mutate()}
            loading={receiveMutation.isPending}
            disabled={!warehouseId || Object.keys(quantities).length === 0}
          >
            Confirmar recepción
          </Button>
        </Card>
      ) : null}
    </div>
  )
}
