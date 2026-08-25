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
  Modal,
  SupplierSelector,
  Table,
} from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { procurementService } from '../../services/procurementService'
import type { PurchaseOrder } from '../../types/procurement'

export function PurchaseOrdersPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const [modalOpen, setModalOpen] = useState(false)
  const [supplierId, setSupplierId] = useState<string | null>(null)
  const [description, setDescription] = useState('')
  const [quantity, setQuantity] = useState('')
  const [unitPrice, setUnitPrice] = useState('')
  const queryClient = useQueryClient()

  const suppliersQuery = useQuery({
    queryKey: ['procurement', 'suppliers', activeCompanyId],
    queryFn: () => procurementService.listSuppliers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const ordersQuery = useQuery({
    queryKey: ['procurement', 'purchase-orders', activeCompanyId],
    queryFn: () => procurementService.listPurchaseOrders(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['procurement', 'purchase-orders', activeCompanyId] })

  const createMutation = useMutation({
    mutationFn: () =>
      procurementService.createPurchaseOrder({
        companyId: activeCompanyId as string,
        supplierId: supplierId as string,
        currencyCode: 'HNL',
        lines: [{ description, quantity, unitPrice }],
      }),
    onSuccess: () => {
      invalidate()
      setModalOpen(false)
      setSupplierId(null)
      setDescription('')
      setQuantity('')
      setUnitPrice('')
    },
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => procurementService.approvePurchaseOrder(id),
    onSuccess: invalidate,
  })
  const sendMutation = useMutation({
    mutationFn: (id: string) => procurementService.sendPurchaseOrder(id),
    onSuccess: invalidate,
  })

  const columns: TableColumn<PurchaseOrder>[] = [
    { key: 'number', header: 'Número', render: (row) => row.poNumber },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{row.status}</Badge> },
    { key: 'total', header: 'Líneas', render: (row) => row.lines.length },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <>
          {row.status === 'DRAFT' ? (
            <Button variant="secondary" onClick={() => approveMutation.mutate(row.id)} loading={approveMutation.isPending}>
              Aprobar
            </Button>
          ) : null}
          {row.status === 'APPROVED' ? (
            <Button variant="secondary" onClick={() => sendMutation.mutate(row.id)} loading={sendMutation.isPending}>
              Enviar
            </Button>
          ) : null}
        </>
      ),
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return <EmptyState title="Configura una compañía primero" description="No hay compañías registradas todavía." />
  }

  const supplierOptions = (suppliersQuery.data ?? []).map((s) => ({ id: s.id, label: s.legalName }))

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Órdenes de compra</h1>
        <Button onClick={() => setModalOpen(true)}>Nueva orden</Button>
      </header>

      <Card>
        {ordersQuery.isLoading ? (
          <LoadingState label="Cargando órdenes…" />
        ) : ordersQuery.isError ? (
          <ErrorState onRetry={() => ordersQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={ordersQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay órdenes de compra."
          />
        )}
      </Card>

      <Modal open={modalOpen} title="Nueva orden de compra" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <SupplierSelector options={supplierOptions} value={supplierId} onChange={setSupplierId} />
          <Input label="Descripción" value={description} onChange={(e) => setDescription(e.target.value)} required />
          <Input label="Cantidad" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
          <Input label="Precio unitario" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} required />
          <Button type="submit" loading={createMutation.isPending} disabled={!supplierId || !description || !quantity || !unitPrice}>
            Guardar
          </Button>
        </form>
      </Modal>
    </div>
  )
}
