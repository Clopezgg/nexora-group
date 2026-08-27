import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, Modal, Select, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { procurementService } from '../../services/procurementService'
import type { PurchaseOrder, Quotation, Rfq } from '../../types/procurement'

/** NXR-REQ-0044. `/abastecimiento/comparativos` ya existía como entrada
 * reservada ("Comparativos") en navigation.ts. RFQ (NXR-REQ-0042) y
 * Supplier Quotations (NXR-REQ-0043) fueron construidos deliberadamente
 * "backend-only" (ver docs/REQUIREMENTS_TRACEABILITY.md) -- esta es la
 * primera y única pantalla que los hace visibles, porque Bid Comparison
 * es literalmente el punto donde alguien necesita verlos lado a lado.
 * `quotation_total()` por cotización ya existía; el cuadro comparativo
 * real reutiliza `GET /rfqs/{id}/quotations`, que ahora también expone
 * delivery_days/payment_terms/valid_until -- los criterios de comparación
 * más allá del precio (ver el fix en el mismo slice). */
export function BidComparisonPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const [selectedRfqId, setSelectedRfqId] = useState<string | null>(null)
  const [rfqModalOpen, setRfqModalOpen] = useState(false)
  const [quoteModalOpen, setQuoteModalOpen] = useState(false)
  const [lastCreatedPO, setLastCreatedPO] = useState<PurchaseOrder | null>(null)

  const suppliersQuery = useQuery({
    queryKey: ['procurement', 'suppliers', activeCompanyId],
    queryFn: () => procurementService.listSuppliers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const rfqsQuery = useQuery({
    queryKey: ['procurement', 'rfqs', activeCompanyId],
    queryFn: () => procurementService.listRfqs(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const quotationsQuery = useQuery({
    queryKey: ['procurement', 'quotations', selectedRfqId],
    queryFn: () => procurementService.listQuotations(selectedRfqId as string),
    enabled: Boolean(selectedRfqId),
  })

  const suppliers = suppliersQuery.data ?? []
  const supplierNameById = new Map(suppliers.map((s) => [s.id, s.legalName]))

  const selectWinnerMutation = useMutation({
    mutationFn: (supplierQuotationId: string) =>
      procurementService.createPurchaseOrderFromQuotation({
        companyId: activeCompanyId as string,
        supplierQuotationId,
      }),
    onSuccess: (order) => {
      setLastCreatedPO(order)
      queryClient.invalidateQueries({ queryKey: ['procurement', 'quotations', selectedRfqId] })
    },
    onError: (error) => handleMutationError(error, 'Seleccionar cotización ganadora'),
  })

  const rfqColumns: TableColumn<Rfq>[] = [
    { key: 'rfqNumber', header: 'RFQ', render: (row) => row.rfqNumber },
    { key: 'dueDate', header: 'Fecha límite', render: (row) => row.dueDate ?? '—' },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{row.status}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <Button variant="ghost" onClick={() => setSelectedRfqId(row.id)}>
          Comparar
        </Button>
      ),
    },
  ]

  const quotationColumns: TableColumn<Quotation>[] = [
    {
      key: 'supplierId',
      header: 'Proveedor',
      render: (row) => supplierNameById.get(row.supplierId) ?? row.supplierId,
    },
    { key: 'total', header: 'Total', render: (row) => `${row.currencyCode} ${row.total}` },
    { key: 'deliveryDays', header: 'Días de entrega', render: (row) => row.deliveryDays ?? '—' },
    { key: 'paymentTerms', header: 'Condiciones de pago', render: (row) => row.paymentTerms ?? '—' },
    { key: 'validUntil', header: 'Vigente hasta', render: (row) => row.validUntil ?? '—' },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{row.status}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <Button
          loading={selectWinnerMutation.isPending}
          onClick={() => selectWinnerMutation.mutate(row.id)}
        >
          Seleccionar ganadora
        </Button>
      ),
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="scale"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Comparativos de cotizaciones</h1>
        <Button onClick={() => setRfqModalOpen(true)} disabled={suppliers.length === 0}>
          Nueva RFQ
        </Button>
      </header>
      {suppliers.length === 0 ? (
        <p className="nx-field__error">Necesitas al menos un proveedor registrado primero.</p>
      ) : null}

      <Card>
        {rfqsQuery.isLoading ? (
          <LoadingState label="Cargando RFQ…" />
        ) : rfqsQuery.isError ? (
          <ErrorState onRetry={() => rfqsQuery.refetch()} />
        ) : (
          <Table
            columns={rfqColumns}
            rows={rfqsQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay RFQ registradas."
          />
        )}
      </Card>

      {selectedRfqId ? (
        <Card title="Comparativo">
          <header className="nx-page__header">
            <Button variant="secondary" onClick={() => setQuoteModalOpen(true)} disabled={suppliers.length === 0}>
              Registrar cotización
            </Button>
          </header>
          {lastCreatedPO ? (
            <p className="nx-field__label">
              Orden de compra creada: {lastCreatedPO.poNumber} ({lastCreatedPO.status})
            </p>
          ) : null}
          {quotationsQuery.isLoading ? (
            <LoadingState label="Cargando cotizaciones…" />
          ) : quotationsQuery.isError ? (
            <ErrorState onRetry={() => quotationsQuery.refetch()} />
          ) : (
            <Table
              columns={quotationColumns}
              rows={quotationsQuery.data ?? []}
              getRowKey={(row) => row.id}
              emptyMessage="Esta RFQ todavía no tiene cotizaciones registradas."
            />
          )}
        </Card>
      ) : null}

      <NewRfqModal
        open={rfqModalOpen}
        companyId={activeCompanyId}
        suppliers={suppliers}
        onClose={() => setRfqModalOpen(false)}
        onCreated={(rfq) => {
          queryClient.invalidateQueries({ queryKey: ['procurement', 'rfqs', activeCompanyId] })
          setSelectedRfqId(rfq.id)
        }}
      />
      {selectedRfqId ? (
        <NewQuotationModal
          open={quoteModalOpen}
          rfqId={selectedRfqId}
          suppliers={suppliers}
          onClose={() => setQuoteModalOpen(false)}
          onCreated={() => queryClient.invalidateQueries({ queryKey: ['procurement', 'quotations', selectedRfqId] })}
        />
      ) : null}
    </div>
  )
}

function NewRfqModal({
  open,
  companyId,
  suppliers,
  onClose,
  onCreated,
}: {
  open: boolean
  companyId: string
  suppliers: { id: string; legalName: string }[]
  onClose: () => void
  onCreated: (rfq: Rfq) => void
}) {
  const [supplierId, setSupplierId] = useState('')
  const handleMutationError = useMutationError()

  const mutation = useMutation({
    mutationFn: () => procurementService.createRfq({ companyId, supplierIds: [supplierId] }),
    onSuccess: (rfq) => {
      onCreated(rfq)
      onClose()
      setSupplierId('')
    },
    onError: (error) => handleMutationError(error, 'Crear RFQ'),
  })

  return (
    <Modal open={open} title="Nueva RFQ" onClose={onClose}>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <Select name="rfqSupplierId" label="Proveedor" value={supplierId} onChange={(e) => setSupplierId(e.target.value)} required>
          <option value="" disabled>
            Selecciona un proveedor
          </option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.legalName}
            </option>
          ))}
        </Select>
        <Button type="submit" loading={mutation.isPending} disabled={!supplierId}>
          Guardar
        </Button>
        {mutation.isError ? <p className="nx-field__error">{String(mutation.error)}</p> : null}
      </form>
    </Modal>
  )
}

function NewQuotationModal({
  open,
  rfqId,
  suppliers,
  onClose,
  onCreated,
}: {
  open: boolean
  rfqId: string
  suppliers: { id: string; legalName: string }[]
  onClose: () => void
  onCreated: () => void
}) {
  const [form, setForm] = useState({
    supplierId: '',
    currencyCode: 'HNL',
    deliveryDays: '',
    paymentTerms: '',
    description: '',
    quantity: '',
    unitPrice: '',
  })
  const handleMutationError = useMutationError()

  const mutation = useMutation({
    mutationFn: () =>
      procurementService.createQuotation(rfqId, {
        supplierId: form.supplierId,
        currencyCode: form.currencyCode,
        deliveryDays: form.deliveryDays ? Number(form.deliveryDays) : undefined,
        paymentTerms: form.paymentTerms || undefined,
        lines: [{ description: form.description, quantity: form.quantity, unitPrice: form.unitPrice }],
      }),
    onSuccess: () => {
      onCreated()
      onClose()
      setForm({ supplierId: '', currencyCode: 'HNL', deliveryDays: '', paymentTerms: '', description: '', quantity: '', unitPrice: '' })
    },
    onError: (error) => handleMutationError(error, 'Registrar cotización'),
  })

  return (
    <Modal open={open} title="Registrar cotización" onClose={onClose}>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <Select
          name="quoteSupplierId"
          label="Proveedor"
          value={form.supplierId}
          onChange={(e) => setForm({ ...form, supplierId: e.target.value })}
          required
        >
          <option value="" disabled>
            Selecciona un proveedor
          </option>
          {suppliers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.legalName}
            </option>
          ))}
        </Select>
        <Input
          name="deliveryDays"
          label="Días de entrega"
          value={form.deliveryDays}
          onChange={(e) => setForm({ ...form, deliveryDays: e.target.value })}
        />
        <Input
          name="paymentTerms"
          label="Condiciones de pago"
          value={form.paymentTerms}
          onChange={(e) => setForm({ ...form, paymentTerms: e.target.value })}
        />
        <Input
          name="description"
          label="Descripción"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          required
        />
        <Input
          name="quantity"
          label="Cantidad"
          value={form.quantity}
          onChange={(e) => setForm({ ...form, quantity: e.target.value })}
          required
        />
        <Input
          name="unitPrice"
          label="Precio unitario"
          value={form.unitPrice}
          onChange={(e) => setForm({ ...form, unitPrice: e.target.value })}
          required
        />
        <Button
          type="submit"
          loading={mutation.isPending}
          disabled={!form.supplierId || !form.description || !form.quantity || !form.unitPrice}
        >
          Guardar
        </Button>
        {mutation.isError ? <p className="nx-field__error">{String(mutation.error)}</p> : null}
      </form>
    </Modal>
  )
}
