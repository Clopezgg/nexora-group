import { useEffect, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Badge, LoadingState, Table, type TableColumn } from '../../design-system'
import { ApiError } from '../../services/httpClient'
import {
  contractPaymentService,
  type ContractInstallment,
} from '../../services/contractPaymentService'
import { procurementService } from '../../services/procurementService'
import { SUPPLIER_CONTRACT_CATEGORY_LABELS } from '../../types/procurement'
import { formatMoney } from '../../utils/currency'

export interface ContractAllocationDraft {
  installmentId: string
  amountApplied: string
}

const STATUS_TONE: Record<string, 'neutral' | 'warning' | 'danger' | 'success'> = {
  PAID: 'success',
  PARTIALLY_PAID: 'warning',
  OVERDUE: 'danger',
  DUE: 'warning',
  UPCOMING: 'neutral',
  CANCELLED: 'neutral',
}

/**
 * Contexto contractual dentro del pago real (ORDEN MAESTRA §20–§25).
 *
 * Cuando la factura está ligada a un contrato de ejecución con plan de pagos,
 * el formulario de pago muestra: Contrato / Beneficiario / Valor contractual /
 * Pagado acumulado / Saldo contractual, el historial de cuotas con su estado
 * REAL (Período / Programado / Retención / Neto / Pagado / Pendiente / Estado)
 * y —al escribir el monto— la propuesta FIFO automática que liquidará las
 * cuotas más antiguas primero. Esa propuesta es la que genera los
 * `ContractPaymentAllocation` al confirmar el pago.
 */
export function ContractInstallmentPanel({
  companyId,
  supplierContractId,
  amount,
  asOf,
  onAllocationsChange,
}: {
  companyId: string
  supplierContractId: string
  amount: number | null
  asOf: string
  onAllocationsChange: (allocations: ContractAllocationDraft[]) => void
}) {
  const scheduleQuery = useQuery({
    queryKey: ['contract-payments', 'by-contract', supplierContractId],
    queryFn: () => contractPaymentService.getByContract(supplierContractId),
    retry: false,
    enabled: Boolean(supplierContractId),
  })
  const scheduleId = scheduleQuery.data?.id
  const currency = scheduleQuery.data?.currencyCode ?? 'HNL'

  const summaryQuery = useQuery({
    queryKey: ['contract-payments', 'summary', scheduleId],
    queryFn: () => contractPaymentService.summary(scheduleId as string, asOf),
    enabled: Boolean(scheduleId),
  })
  const contractsQuery = useQuery({
    queryKey: ['procurement', 'contracts', companyId],
    queryFn: () => procurementService.listContracts(companyId),
    enabled: Boolean(companyId),
  })
  const contract = (contractsQuery.data ?? []).find((c) => c.id === supplierContractId)

  const fifoQuery = useQuery({
    queryKey: ['contract-payments', 'fifo', scheduleId, amount, asOf],
    queryFn: () => contractPaymentService.fifoPreview(scheduleId as string, String(amount), asOf),
    enabled: Boolean(scheduleId) && Boolean(amount) && (amount ?? 0) > 0,
  })

  const proposal = useMemo(() => fifoQuery.data ?? [], [fifoQuery.data])
  const proposedTotal = proposal.reduce((acc, p) => acc + Number(p.amountApplied), 0)
  const coversFullAmount =
    amount != null && amount > 0 && Math.abs(proposedTotal - amount) < 0.005

  useEffect(() => {
    // El backend exige que la suma de asignaciones iguale EXACTAMENTE el monto
    // pagado. Si el pago excede el saldo del plan, no se asignan cuotas (el
    // pago procede igual, sin subledger contractual).
    onAllocationsChange(
      coversFullAmount
        ? proposal.map((p) => ({ installmentId: p.installmentId, amountApplied: p.amountApplied }))
        : [],
    )
  }, [proposal, coversFullAmount, onAllocationsChange])

  const notFound = scheduleQuery.error instanceof ApiError && scheduleQuery.error.status === 404
  if (notFound) {
    return (
      <p className="nx-field__hint" role="status">
        Este contrato de ejecución todavía no tiene plan de pagos, así que este pago no se
        asignará a cuotas contractuales. Crea el plan desde Abastecimiento → Contratos.
      </p>
    )
  }
  if (scheduleQuery.isLoading) return <LoadingState label="Cargando contexto contractual…" />

  const installmentColumns: TableColumn<ContractInstallment>[] = [
    { key: 'periodLabel', header: 'Período', render: (r) => r.periodLabel },
    { key: 'scheduled', header: 'Programado', numeric: true, render: (r) => formatMoney(r.scheduledAmount, currency) },
    { key: 'retention', header: 'Retención', numeric: true, render: (r) => formatMoney(r.retentionAmount, currency) },
    { key: 'net', header: 'Neto', numeric: true, render: (r) => formatMoney(r.netDue, currency) },
    { key: 'paid', header: 'Pagado', numeric: true, render: (r) => formatMoney(r.paid, currency) },
    { key: 'remaining', header: 'Pendiente', numeric: true, render: (r) => formatMoney(r.remaining, currency) },
    {
      key: 'status',
      header: 'Estado',
      render: (r) => <Badge tone={STATUS_TONE[r.status] ?? 'neutral'}>{r.status}</Badge>,
    },
  ]

  const s = summaryQuery.data
  return (
    <div className="nx-contract-context">
      <dl className="nx-voucher-preview">
        {contract ? (
          <>
            <div>
              <dt>Contrato</dt>
              <dd>{contract.contractNumber}</dd>
            </div>
            <div>
              <dt>Categoría</dt>
              <dd>
                {SUPPLIER_CONTRACT_CATEGORY_LABELS[contract.contractCategory] ??
                  contract.contractCategory}
              </dd>
            </div>
          </>
        ) : null}
        {s ? (
          <>
            <div><dt>Valor contractual</dt><dd>{formatMoney(s.contractValue, currency)}</dd></div>
            <div><dt>Pagado acumulado</dt><dd>{formatMoney(s.paidAccumulated, currency)}</dd></div>
            <div><dt>Saldo contractual</dt><dd>{formatMoney(s.contractBalance, currency)}</dd></div>
            <div><dt>Saldo vencido</dt><dd>{formatMoney(s.overdueBalance, currency)}</dd></div>
            <div>
              <dt>Próxima cuota</dt>
              <dd>
                {s.nextDuePeriod
                  ? `${s.nextDuePeriod} · ${formatMoney(s.nextDueAmount ?? '0', currency)}`
                  : '—'}
              </dd>
            </div>
          </>
        ) : null}
      </dl>

      <p className="nx-field__label">Historial de cuotas</p>
      <Table
        columns={installmentColumns}
        rows={scheduleQuery.data?.installments ?? []}
        getRowKey={(r) => r.installmentId}
        emptyMessage="El plan no tiene cuotas."
      />

      {amount != null && amount > 0 ? (
        <div className="nx-contract-context__fifo" role="status">
          {fifoQuery.isLoading ? (
            <span className="nx-field__hint">Calculando asignación FIFO…</span>
          ) : coversFullAmount ? (
            <>
              <p className="nx-field__label">Asignación automática (FIFO)</p>
              <ul className="nx-contract-context__alloc">
                {proposal.map((p) => (
                  <li key={p.installmentId}>
                    Cuota <strong>{p.periodLabel}</strong> ← {formatMoney(p.amountApplied, currency)}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="nx-field__error">
              El monto ({formatMoney(amount, currency)}) excede el saldo pendiente del plan
              ({formatMoney(proposedTotal, currency)}). Este pago se registrará sin asignación a
              cuotas contractuales.
            </p>
          )}
        </div>
      ) : null}
    </div>
  )
}
