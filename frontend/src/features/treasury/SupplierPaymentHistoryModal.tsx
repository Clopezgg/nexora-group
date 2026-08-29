import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Badge,
  Button,
  ErrorState,
  Input,
  LoadingState,
  Modal,
  Table,
  type TableColumn,
} from '../../design-system'
import { useMutationError } from '../../hooks/useMutationError'
import { apService, type SupplierInvoice, type SupplierPayment } from '../../services/apArService'
import { formatMoney } from '../../utils/currency'
import type { TreasuryAccount } from '../../types/treasury'

export function SupplierPaymentHistoryModal({
  invoice,
  treasuryAccounts,
  onClose,
  onReversed,
}: {
  invoice: SupplierInvoice
  treasuryAccounts: TreasuryAccount[]
  onClose: () => void
  onReversed: () => void
}) {
  const handleMutationError = useMutationError()
  const [reversePayment, setReversePayment] = useState<SupplierPayment | null>(null)
  const [reason, setReason] = useState('')
  const paymentsQuery = useQuery({
    queryKey: ['ap', 'supplier-payments', invoice.id],
    queryFn: () => apService.listPayments(invoice.id),
  })
  const accountNames = new Map(treasuryAccounts.map((account) => [account.id, account.name]))

  const executeReverse = useMutation({
    mutationFn: ({ paymentId, reasonText }: { paymentId: string; reasonText: string }) =>
      apService.reversePayment(paymentId, reasonText),
    onSuccess: () => {
      setReversePayment(null)
      setReason('')
      onReversed()
    },
    onError: (error) => handleMutationError(error, 'Revertir pago'),
  })

  const columns: TableColumn<SupplierPayment>[] = [
    { key: 'date', header: 'Fecha', render: (row) => row.paymentDate },
    {
      key: 'account',
      header: 'Cuenta pagadora',
      render: (row) => accountNames.get(row.treasuryAccountId) ?? 'Cuenta de Tesorería',
    },
    {
      key: 'amount',
      header: 'Monto',
      render: (row) => formatMoney(Number(row.amount), invoice.currencyCode),
    },
    {
      key: 'document',
      header: 'Documento GL',
      render: (row) => <code>{row.accountingDocumentId.slice(0, 8)}…</code>,
    },
    {
      key: 'reversal',
      header: 'Reversal',
      render: (row) =>
        row.reversalAccountingDocumentId ? (
          <div>
            <Badge>Revertido</Badge>
            <div className="nx-field__hint">
              {row.reversedAt ? new Date(row.reversedAt).toLocaleString() : ''}
            </div>
            <div className="nx-field__hint">{row.reversalReason ?? ''}</div>
          </div>
        ) : (
          <Badge>Vigente</Badge>
        ),
    },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) =>
        row.reversalAccountingDocumentId ? null : (
          <Button variant="secondary" onClick={() => setReversePayment(row)}>
            Revertir
          </Button>
        ),
    },
  ]

  return (
    <Modal open title={`Historial de pagos · ${invoice.invoiceNumber}`} onClose={onClose}>
      {paymentsQuery.isLoading ? (
        <LoadingState label="Cargando historial…" />
      ) : paymentsQuery.isError ? (
        <ErrorState
          description="No se pudo cargar el historial de pagos."
          onRetry={() => paymentsQuery.refetch()}
        />
      ) : (
        <Table
          columns={columns}
          rows={paymentsQuery.data ?? []}
          getRowKey={(row) => row.id}
          emptyMessage="No hay pagos registrados para esta factura."
        />
      )}

      {reversePayment ? (
        <div className="nx-treasury__form">
          <p><strong>Reversal formal</strong></p>
          <p className="nx-field__hint">
            Se conservará el pago original y se creará un asiento inverso. No se elimina historial.
          </p>
          <Input
            label="Motivo"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            required
          />
          <div className="nx-treasury__actions">
            <Button
              variant="secondary"
              onClick={() => {
                setReversePayment(null)
                setReason('')
              }}
            >
              Cancelar
            </Button>
            <Button
              loading={executeReverse.isPending}
              disabled={reason.trim().length < 3}
              onClick={() =>
                executeReverse.mutate({ paymentId: reversePayment.id, reasonText: reason.trim() })
              }
            >
              Confirmar reversal
            </Button>
          </div>
        </div>
      ) : null}
    </Modal>
  )
}
