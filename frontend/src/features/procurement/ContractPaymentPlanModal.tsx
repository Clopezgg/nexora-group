import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Modal,
  Select,
  Table,
  type TableColumn,
} from '../../design-system'
import { ApiError } from '../../services/httpClient'
import { contractPaymentService, type ContractInstallment } from '../../services/contractPaymentService'
import { formatMoney } from '../../utils/currency'
import {
  contractInstallmentKindLabel,
  contractInstallmentStatusLabel,
} from '../../utils/statusLabels'
import type { SupplierContract } from '../../types/procurement'

const STATUS_TONE: Record<string, 'neutral' | 'warning' | 'danger' | 'success'> = {
  PAID: 'success',
  PARTIALLY_PAID: 'warning',
  OVERDUE: 'danger',
  DUE: 'warning',
  UPCOMING: 'neutral',
  CANCELLED: 'neutral',
}

/**
 * Plan de pagos del contrato (CORRECTIVA §16-§20, §25-§26, §63).
 *
 * El ANTICIPO es parte del plan y NO consume una de las N mensualidades. El
 * backend calcula las cuotas: base regular = valor − anticipo, cuotas iguales y
 * la última absorbe el redondeo (Decimal exacto). El frontend solo presenta.
 */
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
  const nowMonth = new Date().toISOString().slice(0, 7)
  const [form, setForm] = useState({ firstPeriod: nowMonth, regularMonths: '7', dueDay: '1' })

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
      contractPaymentService.createContractPlan({
        supplierContractId: contract.id,
        regularMonths: Number(form.regularMonths),
        dueDay: Number(form.dueDay),
        firstPeriod: `${form.firstPeriod}-01`,
        advanceAmount: contract.advanceAmount ?? undefined,
        advanceDueDate: contract.advanceDueDate ?? undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-payments'] })
      queryClient.invalidateQueries({ queryKey: ['procurement', 'contracts'] })
      queryClient.invalidateQueries({ queryKey: ['project'] })
    },
  })

  const notFound = scheduleQuery.error instanceof ApiError && scheduleQuery.error.status === 404
  const currency = scheduleQuery.data?.currencyCode ?? currencyCode

  const advancePreview = useMemo(() => {
    const value = Number(contract.value)
    const advance = Number(contract.advanceAmount ?? 0)
    const months = Math.max(1, Number(form.regularMonths) || 1)
    const base = value - advance
    const per = Math.floor((base / months) * 100) / 100
    return { advance, base, per, last: base - per * (months - 1) }
  }, [contract.value, contract.advanceAmount, form.regularMonths])

  const columns: TableColumn<ContractInstallment>[] = [
    {
      key: 'kind',
      header: 'Tipo',
      render: (r) => (
        <Badge tone={r.installmentKind === 'ADVANCE' ? 'info' : 'neutral'}>
          {contractInstallmentKindLabel(r.installmentKind)}
        </Badge>
      ),
    },
    { key: 'n', header: '#', render: (r) => (r.installmentKind === 'REGULAR' ? String(r.regularNumber) : '—') },
    { key: 'due', header: 'Vencimiento', render: (r) => r.dueDate },
    { key: 'sched', header: 'Programado', numeric: true, render: (r) => formatMoney(r.scheduledAmount, currency) },
    {
      key: 'ret',
      header: 'Retención',
      numeric: true,
      render: (r) => (Number(r.retentionAmount) > 0 ? formatMoney(r.retentionAmount, currency) : '—'),
    },
    { key: 'net', header: 'Neto', numeric: true, render: (r) => formatMoney(r.netDue, currency) },
    { key: 'paid', header: 'Pagado', numeric: true, render: (r) => formatMoney(r.paid, currency) },
    { key: 'rem', header: 'Pendiente', numeric: true, render: (r) => formatMoney(r.remaining, currency) },
    {
      key: 'status',
      header: 'Estado',
      render: (r) => (
        <Badge tone={STATUS_TONE[r.status] ?? 'neutral'}>{contractInstallmentStatusLabel(r.status)}</Badge>
      ),
    },
  ]

  return (
    <Modal
      open
      title={`Plan de pagos · ${contract.contractNumber}`}
      onClose={onClose}
      size="wide"
    >
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
            description="El anticipo pactado del contrato entra al plan automáticamente. Indica cuántas mensualidades y el día de pago; el sistema calcula los importes (la última cuota absorbe el redondeo)."
          />
          <dl className="nx-voucher-preview">
            <div><dt>Valor contractual</dt><dd>{formatMoney(contract.value, currency)}</dd></div>
            <div>
              <dt>Anticipo pactado</dt>
              <dd>
                {contract.advanceAmount
                  ? `${formatMoney(contract.advanceAmount, currency)}${contract.advanceDueDate ? ` · vence ${contract.advanceDueDate}` : ''}`
                  : 'Sin anticipo'}
              </dd>
            </div>
            <div><dt>Base de mensualidades</dt><dd>{formatMoney(String(advancePreview.base), currency)}</dd></div>
            <div>
              <dt>Cuota sugerida</dt>
              <dd>
                {formatMoney(String(advancePreview.per), currency)} · última{' '}
                {formatMoney(String(advancePreview.last), currency)}
              </dd>
            </div>
          </dl>
          <Input
            label="Primer período (mensualidad 1)"
            type="month"
            value={form.firstPeriod}
            onChange={(e) => setForm({ ...form, firstPeriod: e.target.value })}
            required
          />
          <Input
            label="N.º de mensualidades"
            type="number"
            min={1}
            value={form.regularMonths}
            onChange={(e) => setForm({ ...form, regularMonths: e.target.value })}
            required
          />
          <Select
            label="Día de pago de cada mes"
            value={form.dueDay}
            onChange={(e) => setForm({ ...form, dueDay: e.target.value })}
          >
            {Array.from({ length: 31 }, (_, i) => String(i + 1)).map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </Select>
          <Button
            type="submit"
            loading={createMutation.isPending}
            disabled={!form.firstPeriod || !form.regularMonths}
          >
            Crear plan
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
              <div><dt>Anticipo programado</dt><dd>{formatMoney(summaryQuery.data.advanceScheduled, currency)}</dd></div>
              <div><dt>Anticipo pagado</dt><dd>{formatMoney(summaryQuery.data.advancePaid, currency)}</dd></div>
              <div><dt>Base regular</dt><dd>{formatMoney(summaryQuery.data.regularScheduled, currency)}</dd></div>
              <div><dt>Total programado</dt><dd>{formatMoney(summaryQuery.data.totalContractualScheduled, currency)}</dd></div>
              <div><dt>Programado a fecha</dt><dd>{formatMoney(summaryQuery.data.totalScheduledToDate, currency)}</dd></div>
              <div><dt>Pagado acumulado</dt><dd>{formatMoney(summaryQuery.data.paidAccumulated, currency)}</dd></div>
              <div><dt>Saldo contractual</dt><dd>{formatMoney(summaryQuery.data.contractBalance, currency)}</dd></div>
              <div><dt>Retención pendiente</dt><dd>{formatMoney(summaryQuery.data.retentionOutstanding, currency)}</dd></div>
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
          <div style={{ overflowX: 'auto' }}>
            <Table
              columns={columns}
              rows={scheduleQuery.data?.installments ?? []}
              getRowKey={(r) => r.installmentId}
              emptyMessage="El plan no tiene cuotas."
            />
          </div>
        </>
      )}
    </Modal>
  )
}
