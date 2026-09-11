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
  Select,
  SupplierSelector,
  Table,
  Textarea,
} from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { procurementService } from '../../services/procurementService'
import { apService } from '../../services/apArService'
import type { PurchaseOrder, ThreeWayMatch } from '../../types/procurement'

export function PurchaseOrdersPage() {
  const { activeCompanyId, activeCompany, isLoading: loadingCompanies } = useActiveCompany()
  const handleMutationError = useMutationError()
  const [modalOpen, setModalOpen] = useState(false)
  const [supplierId, setSupplierId] = useState<string | null>(null)
  const [description, setDescription] = useState('')
  const [quantity, setQuantity] = useState('')
  const [unitPrice, setUnitPrice] = useState('')
  const [fulfillmentType, setFulfillmentType] = useState<'GOODS' | 'SERVICE'>('GOODS')
  const [matchOrder, setMatchOrder] = useState<PurchaseOrder | null>(null)
  const [matchInvoiceId, setMatchInvoiceId] = useState('')
  const [invoiceQuantity, setInvoiceQuantity] = useState('')
  const [overrideMatch, setOverrideMatch] = useState<ThreeWayMatch | null>(null)
  const [overrideReason, setOverrideReason] = useState('')
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
  const invoicesQuery = useQuery({
    queryKey: ['ap', 'supplier-invoices', activeCompanyId],
    queryFn: () => apService.listInvoices(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const matchesQuery = useQuery({
    queryKey: ['procurement', 'three-way-match', activeCompanyId],
    queryFn: () => procurementService.listThreeWayMatches(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['procurement', 'purchase-orders', activeCompanyId] })

  const createMutation = useMutation({
    mutationFn: () =>
      procurementService.createPurchaseOrder({
        companyId: activeCompanyId as string,
        supplierId: supplierId as string,
        currencyCode: activeCompany?.functionalCurrencyCode ?? 'HNL',
        fulfillmentType,
        lines: [{ description, quantity, unitPrice }],
      }),
    onSuccess: () => {
      invalidate()
      setModalOpen(false)
      setSupplierId(null)
      setDescription('')
      setQuantity('')
      setUnitPrice('')
      setFulfillmentType('GOODS')
    },
    onError: (error) => handleMutationError(error, 'Crear orden de compra'),
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => procurementService.approvePurchaseOrder(id),
    onSuccess: invalidate,
    onError: (error) => handleMutationError(error, 'Aprobar orden de compra'),
  })
  const sendMutation = useMutation({
    mutationFn: (id: string) => procurementService.sendPurchaseOrder(id),
    onSuccess: invalidate,
    onError: (error) => handleMutationError(error, 'Enviar orden de compra'),
  })
  const matchMutation = useMutation({
    mutationFn: () => procurementService.runThreeWayMatch({
      purchaseOrderId: matchOrder?.id as string,
      supplierInvoiceId: matchInvoiceId,
      supplierInvoiceQuantity: invoiceQuantity,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'three-way-match', activeCompanyId] })
      setMatchOrder(null)
      setMatchInvoiceId('')
      setInvoiceQuantity('')
    },
    onError: (error) => handleMutationError(error, 'Conciliar factura con orden y recepción'),
  })
  const overrideMutation = useMutation({
    mutationFn: () => procurementService.overrideThreeWayMatch(overrideMatch?.id as string, overrideReason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'three-way-match', activeCompanyId] })
      setOverrideMatch(null)
      setOverrideReason('')
    },
    onError: (error) => handleMutationError(error, 'Autorizar excepción de conciliación'),
  })

  const matchesByOrder = new Map<string, ThreeWayMatch>()
  for (const match of matchesQuery.data ?? []) {
    if (!matchesByOrder.has(match.purchaseOrderId)) matchesByOrder.set(match.purchaseOrderId, match)
  }

  const columns: TableColumn<PurchaseOrder>[] = [
    { key: 'number', header: 'Número', render: (row) => row.poNumber },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{row.status.replaceAll('_', ' ')}</Badge> },
    {
      key: 'match',
      header: 'Conciliación',
      render: (row) => {
        const match = matchesByOrder.get(row.id)
        if (!match) return <span>Sin conciliar</span>
        return (
          <span>
            <Badge tone={match.status === 'MATCHED' ? 'success' : 'warning'}>
              {match.status === 'MATCHED' ? 'Conciliada' : 'Excepción'}
            </Badge>
            {match.status === 'EXCEPTION' && !match.overriddenAt ? (
              <Button variant="ghost" onClick={() => setOverrideMatch(match)}>
                Autorizar excepción
              </Button>
            ) : null}
          </span>
        )
      },
    },
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
          {['SENT', 'PARTIALLY_RECEIVED', 'RECEIVED'].includes(row.status) ? (
            <Button
              variant="secondary"
              aria-label={`Conciliar factura de ${row.poNumber}`}
              onClick={() => setMatchOrder(row)}
            >
              Conciliar factura
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
          <Select
            label="Tipo de recepción"
            value={fulfillmentType}
            onChange={(event) => setFulfillmentType(event.target.value as 'GOODS' | 'SERVICE')}
          >
            <option value="GOODS">Bienes · recepción de mercadería</option>
            <option value="SERVICE">Servicios · aceptación por período</option>
          </Select>
          <Input label="Descripción" value={description} onChange={(e) => setDescription(e.target.value)} required />
          <Input label="Cantidad" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
          <Input label="Precio unitario" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} required />
          <Button type="submit" loading={createMutation.isPending} disabled={!supplierId || !description || !quantity || !unitPrice}>
            Guardar
          </Button>
        </form>
      </Modal>

      <Modal
        open={Boolean(matchOrder)}
        title={`Conciliación tres vías · ${matchOrder?.poNumber ?? ''}`}
        onClose={() => setMatchOrder(null)}
      >
        <form onSubmit={(event) => { event.preventDefault(); matchMutation.mutate() }}>
          <Select
            label="Factura de proveedor"
            value={matchInvoiceId}
            onChange={(event) => setMatchInvoiceId(event.target.value)}
            required
          >
            <option value="">Selecciona una factura vinculada</option>
            {(invoicesQuery.data ?? [])
              .filter((invoice) => invoice.purchaseOrderId === matchOrder?.id)
              .map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.invoiceNumber}</option>)}
          </Select>
          <Input
            label="Cantidad facturada"
            value={invoiceQuantity}
            onChange={(event) => setInvoiceQuantity(event.target.value)}
            inputMode="decimal"
            required
          />
          <p>El importe se toma de la factura; no puede capturarse manualmente.</p>
          <Button
            type="submit"
            loading={matchMutation.isPending}
            disabled={!matchInvoiceId || !invoiceQuantity}
          >
            Ejecutar conciliación
          </Button>
        </form>
      </Modal>

      <Modal
        open={Boolean(overrideMatch)}
        title="Autorizar excepción de conciliación"
        onClose={() => setOverrideMatch(null)}
      >
        <form onSubmit={(event) => { event.preventDefault(); overrideMutation.mutate() }}>
          <Textarea
            label="Motivo de autorización"
            value={overrideReason}
            onChange={(event) => setOverrideReason(event.target.value)}
            minLength={10}
            required
          />
          <Button type="submit" loading={overrideMutation.isPending} disabled={overrideReason.trim().length < 10}>
            Autorizar excepción
          </Button>
        </form>
      </Modal>
    </div>
  )
}
