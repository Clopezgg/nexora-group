import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Modal,
  Table,
  type TableColumn,
} from '../../design-system'
import { ApiError } from '../../services/httpClient'
import { contractPaymentService, type ContractInstallment } from '../../services/contractPaymentService'
import { formatMoney } from '../../utils/currency'
import type { SupplierContract } from '../../types/procurement'

const STATUS_TONE: Record<string, 'neutral' | 'warning' | 'danger' | 'success'> = {
  PAID: 'success',
  PARTIALLY_PAID: 'warning',
  OVERDUE: 'danger',
  DUE: 'warning',
  UPCOMING: 'neutral',
  CANCELLED: 'neutral',
}

/** Plan de pagos de un contrato (orden maestra final §21-§23). Muestra el
 * historial de cuotas con estado REAL (calculado desde allocations), el
 * resumen contractual y —si no existe— permite crear un plan mensual. */
export function ContractPaymentPlanModal({
  contract,
  currencyCode,
  onClose,
}: {
  contract: SupplierContract
  currencyCode: string
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [form, setForm] = useState({ startPeriod: '', months: '12', monthlyAmount: '' })

  const scheduleQuery = useQuery({
    queryKey: ['contract-payments', 'by-contract', contract.id],
    queryFn: () => contractPaymentService.getByContract(contract.id),
    retry: false,
    enabled: Boolean(contract.id),
  })
  const scheduleId = scheduleQuery.data?.id
  const summaryQuery = useQuery({
    queryKey: ['contract-payments', 'summary', scheduleId],
    queryFn: () => contractPaymentService.summary(scheduleId as string),
    enabled: Boolean(scheduleId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      contractPaymentService.createMonthlySchedule({
        supplierContractId: contract.id,
        startPeriod: form.startPeriod,
        months: Number(form.months),
        monthlyAmount: form.monthlyAmount,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-payments', 'by-contract', contract.id] })
    },
  })

  const notFound = scheduleQuery.error instanceof ApiError && scheduleQuery.error.status === 404
  const currency = scheduleQuery.data?.currencyCode ?? currencyCode

  const columns: TableColumn<ContractInstallment>[] = [
    { key: 'periodLabel', header: 'Período', render: (r) => r.periodLabel },
    { key: 'scheduled', header: 'Programado', numeric: true, render: (r) => formatMoney(r.scheduledAmount, currency) },
    { key: 'paid', header: 'Pagado', numeric: true, render: (r) => formatMoney(r.paid, currency) },
    { key: 'remaining', header: 'Saldo', numeric: true, render: (r) => formatMoney(r.remaining, currency) },
    {
      key: 'status',
      header: 'Estado',
      render: (r) => <Badge tone={STATUS_TONE[r.status] ?? 'neutral'}>{r.status}</Badge>,
    },
  ]

  return (
    <Modal open title={`Plan de pagos · ${contract.contractNumber}`} onClose={onClose}>
      {scheduleQuery.isLoading ? (
        <LoadingState label="Cargando plan…" />
      ) : notFound ? (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <EmptyState
            icon="calendar"
            title="Este contrato aún no tiene plan de pagos"
            description="Crea un plan mensual: se generan cuotas iguales y la última absorbe el redondeo para cuadrar con el valor del contrato."
          />
          <Input
            label="Primer período"
            type="date"
            value={form.startPeriod}
            onChange={(e) => setForm({ ...form, startPeriod: e.target.value })}
            required
          />
          <Input
            label="N.º de cuotas"
            type="number"
            min={1}
            value={form.months}
            onChange={(e) => setForm({ ...form, months: e.target.value })}
            required
          />
          <Input
            label="Cuota mensual"
            inputMode="decimal"
            value={form.monthlyAmount}
            onChange={(e) => setForm({ ...form, monthlyAmount: e.target.value })}
            required
          />
          <Button
            type="submit"
            loading={createMutation.isPending}
            disabled={!form.startPeriod || !form.months || !form.monthlyAmount}
          >
            Crear plan mensual
          </Button>
          {createMutation.isError ? (
            <p className="nx-field__error" role="alert">
              {createMutation.error instanceof ApiError
                ? createMutation.error.message
                : 'No se pudo crear el plan.'}
            </p>
          ) : null}
        </form>
      ) : scheduleQuery.isError ? (
        <ErrorState onRetry={() => scheduleQuery.refetch()} />
      ) : (
        <>
          {summaryQuery.data ? (
            <dl className="nx-voucher-preview">
              <div><dt>Valor contractual</dt><dd>{formatMoney(summaryQuery.data.contractValue, currency)}</dd></div>
              <div><dt>Programado a fecha</dt><dd>{formatMoney(summaryQuery.data.totalScheduledToDate, currency)}</dd></div>
              <div><dt>Pagado acumulado</dt><dd>{formatMoney(summaryQuery.data.paidAccumulated, currency)}</dd></div>
              <div><dt>Saldo contractual</dt><dd>{formatMoney(summaryQuery.data.contractBalance, currency)}</dd></div>
              <div><dt>Saldo vencido</dt><dd>{formatMoney(summaryQuery.data.overdueBalance, currency)}</dd></div>
              <div>
                <dt>Próximo vencimiento</dt>
                <dd>
                  {summaryQuery.data.nextDuePeriod
                    ? `${summaryQuery.data.nextDuePeriod} · ${formatMoney(summaryQuery.data.nextDueAmount ?? '0', currency)}`
                    : '—'}
                </dd>
              </div>
            </dl>
          ) : null}
          <Table
            columns={columns}
            rows={scheduleQuery.data?.installments ?? []}
            getRowKey={(r) => r.installmentId}
            emptyMessage="El plan no tiene cuotas."
          />
        </>
      )}
    </Modal>
  )
}
