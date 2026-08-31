import { useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Button, Input, LoadingState, Modal, Table, type TableColumn } from '../../design-system'
import { useMutationError } from '../../hooks/useMutationError'
import {
  apService,
  type PaymentPlanItem,
  type PaymentPlanItemInput,
  type SupplierInvoice,
} from '../../services/apArService'
import { formatMoney } from '../../utils/currency'

interface DraftRow {
  dueDate: string
  amount: string
}

/**
 * Plan de pago / cuotas de una factura de proveedor (orden maestra Phase 2).
 * La suma de las cuotas debe igualar el total de la factura; el backend es la
 * autoridad — aquí solo se previsualiza para dar feedback inmediato.
 */
export function PaymentPlanModal({
  invoice,
  onClose,
  onSaved,
}: {
  invoice: SupplierInvoice
  onClose: () => void
  onSaved: () => void
}) {
  const handleMutationError = useMutationError()
  const total = Number(invoice.amount) + Number(invoice.taxAmount ?? 0)

  const planQuery = useQuery({
    queryKey: ['ap', 'payment-plan', invoice.id],
    queryFn: () => apService.getPaymentPlan(invoice.id),
  })

  const [rows, setRows] = useState<DraftRow[] | null>(null)
  const draft: DraftRow[] = useMemo(() => {
    if (rows) return rows
    if (planQuery.data && planQuery.data.length > 0) {
      return planQuery.data.map((item) => ({ dueDate: item.dueDate, amount: String(item.amount) }))
    }
    return [{ dueDate: '', amount: '' }]
  }, [rows, planQuery.data])

  const draftTotal = draft.reduce((acc, row) => acc + (Number(row.amount) || 0), 0)
  const balanced = Math.abs(draftTotal - total) < 0.005
  const editable = ['APPROVED', 'SCHEDULED'].includes(invoice.status) && Number(invoice.amountPaid ?? 0) === 0

  const save = useMutation({
    mutationFn: () =>
      apService.setPaymentPlan(
        invoice.id,
        draft.map<PaymentPlanItemInput>((row) => ({
          dueDate: row.dueDate,
          amount: Number(row.amount).toFixed(2),
        })),
      ),
    onSuccess: () => {
      onSaved()
      onClose()
    },
    onError: (error) => handleMutationError(error, 'Guardar plan de pago'),
  })

  const columns: TableColumn<PaymentPlanItem>[] = [
    { key: 'sequence', header: '#', render: (row) => row.sequence },
    { key: 'dueDate', header: 'Vence', render: (row) => row.dueDate },
    { key: 'amount', header: 'Monto', render: (row) => formatMoney(row.amount, invoice.currencyCode) },
  ]

  return (
    <Modal open title={`Plan de pago · ${invoice.invoiceNumber}`} onClose={onClose}>
      <p className="nx-field__hint">
        Total de la factura: <strong>{formatMoney(total, invoice.currencyCode)}</strong>. La suma de
        las cuotas debe coincidir exactamente.
      </p>

      {planQuery.isLoading ? (
        <LoadingState label="Cargando plan…" />
      ) : planQuery.data && planQuery.data.length > 0 ? (
        <Table
          columns={columns}
          rows={planQuery.data}
          getRowKey={(row) => row.id}
          emptyMessage="Sin cuotas"
        />
      ) : null}

      {editable ? (
        <div className="nx-treasury__form" style={{ marginTop: '0.75rem' }}>
          {draft.map((row, index) => (
            <div key={index} className="nx-treasury__actions">
              <Input
                label={`Cuota ${index + 1} · vencimiento`}
                type="date"
                value={row.dueDate}
                onChange={(event) => {
                  const next = [...draft]
                  next[index] = { ...next[index], dueDate: event.target.value }
                  setRows(next)
                }}
              />
              <Input
                label="Monto"
                type="number"
                value={row.amount}
                onChange={(event) => {
                  const next = [...draft]
                  next[index] = { ...next[index], amount: event.target.value }
                  setRows(next)
                }}
              />
              {draft.length > 1 ? (
                <Button
                  variant="secondary"
                  onClick={() => setRows(draft.filter((_, i) => i !== index))}
                >
                  Quitar
                </Button>
              ) : null}
            </div>
          ))}
          <Button variant="secondary" onClick={() => setRows([...draft, { dueDate: '', amount: '' }])}>
            Añadir cuota
          </Button>
          <p className={balanced ? 'nx-field__hint' : 'nx-field__error'} role={balanced ? undefined : 'alert'}>
            Suma de cuotas: {formatMoney(draftTotal, invoice.currencyCode)}{' '}
            {balanced ? '· coincide' : `· debe ser ${formatMoney(total, invoice.currencyCode)}`}
          </p>
          <Button
            loading={save.isPending}
            disabled={!balanced || draft.some((row) => !row.dueDate || !row.amount)}
            onClick={() => save.mutate()}
          >
            Guardar plan de pago
          </Button>
        </div>
      ) : (
        <p className="nx-field__hint">
          El plan solo puede editarse mientras la factura está aprobada o programada y sin pagos aplicados.
        </p>
      )}
    </Modal>
  )
}
