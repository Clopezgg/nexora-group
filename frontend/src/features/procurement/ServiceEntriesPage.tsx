import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Badge, Button, Card, EmptyState, ErrorState, FilePicker, Input, LoadingState, Select, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { procurementService } from '../../services/procurementService'
import { documentService } from '../../services/documentService'
import type { ServiceEntry } from '../../types/procurement'
import { formatMoney } from '../../utils/currency'

const ACCEPTABLE_STATUSES = ['APPROVED', 'SENT', 'PARTIALLY_RECEIVED']

export function ServiceEntriesPage() {
  const { activeCompanyId, activeCompany, isLoading: loadingCompanies } = useActiveCompany()
  const handleMutationError = useMutationError()
  const queryClient = useQueryClient()
  const [purchaseOrderId, setPurchaseOrderId] = useState('')
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  const [progressPercentage, setProgressPercentage] = useState('')
  const [acceptedValue, setAcceptedValue] = useState('')
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null)

  const ordersQuery = useQuery({
    queryKey: ['procurement', 'purchase-orders', activeCompanyId],
    queryFn: () => procurementService.listPurchaseOrders(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const entriesQuery = useQuery({
    queryKey: ['procurement', 'service-entries', activeCompanyId],
    queryFn: () => procurementService.listServiceEntries(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const mutation = useMutation({
    mutationFn: async () => {
      const evidence = evidenceFile
        ? await documentService.uploadEvidence(
          activeCompanyId as string,
          evidenceFile,
          'SERVICE_ENTRY',
          'PURCHASE_ORDER',
          purchaseOrderId,
        )
        : null
      return procurementService.createServiceEntry({
        purchaseOrderId,
        periodStart,
        periodEnd,
        progressPercentage,
        acceptedValue,
        evidenceId: evidence?.id,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'service-entries', activeCompanyId] })
      setPurchaseOrderId('')
      setPeriodStart('')
      setPeriodEnd('')
      setProgressPercentage('')
      setAcceptedValue('')
      setEvidenceFile(null)
    },
    onError: (error) => handleMutationError(error, 'Registrar entrada de servicio'),
  })

  const orders = (ordersQuery.data ?? []).filter((order) => ACCEPTABLE_STATUSES.includes(order.status))
  const orderNumbers = new Map((ordersQuery.data ?? []).map((order) => [order.id, order.poNumber]))
  const currency = activeCompany?.functionalCurrencyCode ?? undefined
  const columns: TableColumn<ServiceEntry>[] = [
    { key: 'number', header: 'Entrada', render: (row) => row.entryNumber },
    { key: 'po', header: 'Orden', render: (row) => orderNumbers.get(row.purchaseOrderId) ?? 'Orden no disponible' },
    { key: 'period', header: 'Período', render: (row) => `${row.periodStart} — ${row.periodEnd}` },
    { key: 'progress', header: 'Avance', numeric: true, render: (row) => `${row.progressPercentage}%` },
    { key: 'value', header: 'Valor aceptado', numeric: true, render: (row) => formatMoney(row.acceptedValue, currency) },
    { key: 'status', header: 'Estado', render: () => <Badge tone="success">Aceptada</Badge> },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) return <EmptyState title="Selecciona una compañía" description="La entrada de servicio requiere una compañía activa." />

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <h1 className="nx-dashboard__title">Entradas de servicio</h1>
          <p className="nx-page__subtitle">Acepta avances ejecutados antes de conciliarlos con la factura del proveedor.</p>
        </div>
        <FilePicker
          label="Evidencia del avance"
          hint="Opcional. Adjunta acta, informe o soporte aceptado; quedará enlazado a la orden y a esta entrada."
          accept="application/pdf,image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif"
          value={evidenceFile}
          onChange={setEvidenceFile}
          disabled={mutation.isPending}
        />
      </header>
      <Card title="Registrar aceptación">
        <Select label="Orden de compra" value={purchaseOrderId} onChange={(event) => setPurchaseOrderId(event.target.value)}>
          <option value="">Selecciona una orden</option>
          {orders.map((order) => <option key={order.id} value={order.id}>{order.poNumber}</option>)}
        </Select>
        <div className="nx-form-grid">
          <Input label="Inicio del período" type="date" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} />
          <Input label="Fin del período" type="date" value={periodEnd} onChange={(event) => setPeriodEnd(event.target.value)} />
          <Input label="Avance aceptado (%)" inputMode="decimal" value={progressPercentage} onChange={(event) => setProgressPercentage(event.target.value)} />
          <Input label="Valor aceptado" inputMode="decimal" value={acceptedValue} onChange={(event) => setAcceptedValue(event.target.value)} />
        </div>
        <Button
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          disabled={!purchaseOrderId || !periodStart || !periodEnd || !progressPercentage || !acceptedValue}
        >
          Registrar entrada
        </Button>
      </Card>
      <Card title="Avances aceptados">
        {entriesQuery.isLoading ? <LoadingState label="Cargando entradas…" /> : entriesQuery.isError ? (
          <ErrorState onRetry={() => entriesQuery.refetch()} />
        ) : (
          <Table columns={columns} rows={entriesQuery.data ?? []} getRowKey={(row) => row.id} emptyMessage="No hay entradas de servicio registradas." />
        )}
      </Card>
    </div>
  )
}
