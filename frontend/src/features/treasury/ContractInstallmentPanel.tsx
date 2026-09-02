import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Badge, Button, LoadingState, Table, type TableColumn } from '../../design-system'
import { ApiError } from '../../services/httpClient'
import {
  contractPaymentService,
  type ContractInstallment,
} from '../../services/contractPaymentService'
import { procurementService } from '../../services/procurementService'
import { SUPPLIER_CONTRACT_CATEGORY_LABELS } from '../../types/procurement'
import {
  contractInstallmentKindLabel,
  contractInstallmentStatusLabel,
} from '../../utils/statusLabels'
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
 * Contexto contractual dentro del pago real (CORRECTIVA §30-§37, §43).
 *
 * El pago DEBE asignarse íntegramente a cuotas del plan (§34/§35): si el monto
 * no se puede repartir exactamente, `onChange` reporta `valid=false` y el
 * formulario de pago bloquea "Confirmar". Nunca se registra un pago contractual
 * "sin asignación".
 *
 * `selectedInstallmentId` (cuota desde la que se inició el pago) es la
 * asignación PRIMARIA (§32); FIFO es sólo una ayuda (§33).
 */
export function ContractInstallmentPanel({
  companyId,
  supplierContractId,
  amount,
  asOf,
  selectedInstallmentId,
  onChange,
}: {
  companyId: string
  supplierContractId: string
  amount: number | null
  asOf: string
  selectedInstallmentId?: string | null
  onChange: (allocations: ContractAllocationDraft[], valid: boolean, hasSchedule: boolean) => void
}) {
  const scheduleQuery = useQuery({
    queryKey: ['contract-payments', 'by-contract', supplierContractId],
    queryFn: () => contractPaymentService.getByContract(supplierContractId),
    retry: false,
    enabled: Boolean(supplierContractId),
  })
  const scheduleId = scheduleQuery.data?.id
  const currency = scheduleQuery.data?.currencyCode ?? 'HNL'
  const [manualId, setManualId] = useState<string>('')

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
  const suppliersQuery = useQuery({
    queryKey: ['procurement', 'suppliers', companyId],
    queryFn: () => procurementService.listSuppliers(companyId),
    enabled: Boolean(companyId),
  })
  const contract = (contractsQuery.data ?? []).find((c) => c.id === supplierContractId)
  const party = (suppliersQuery.data ?? []).find((s) => s.id === contract?.supplierId)
  const beneficiaryVerb = useMemo(() => {
    const role = party?.partyRole
    if (role === 'CONTRACTOR') return 'Registrar pago a contratista'
    if (role === 'BOTH') return 'Registrar pago'
    return 'Registrar pago a proveedor'
  }, [party?.partyRole])

  const installments = useMemo(
    () => scheduleQuery.data?.installments ?? [],
    [scheduleQuery.data],
  )
  const primaryId = manualId || selectedInstallmentId || ''

  // Asignación: cuota primaria primero, luego FIFO sobre el resto (§32/§33).
  const allocation = useMemo(() => {
    if (amount == null || amount <= 0) return { rows: [] as ContractAllocationDraft[], total: 0 }
    let left = Math.round(amount * 100) / 100
    const ordered = [
      ...installments.filter((i) => i.installmentId === primaryId),
      ...installments.filter((i) => i.installmentId !== primaryId),
    ]
    const rows: ContractAllocationDraft[] = []
    for (const i of ordered) {
      if (left <= 0.004) break
      if (i.status === 'CANCELLED') continue
      const rem = Number(i.remaining)
      if (rem <= 0) continue
      const apply = Math.min(left, rem)
      rows.push({ installmentId: i.installmentId, amountApplied: apply.toFixed(2) })
      left = Math.round((left - apply) * 100) / 100
    }
    const total = rows.reduce((acc, r) => acc + Number(r.amountApplied), 0)
    return { rows, total }
  }, [amount, installments, primaryId])

  const covers =
    amount != null && amount > 0 && Math.abs(allocation.total - amount) < 0.005
  const hasSchedule = Boolean(scheduleId)

  // Firma estable del resultado: sólo notificamos al padre cuando cambia de
  // verdad (el padre pasa una arrow inline — nueva cada render).
  const emittedRows = covers ? allocation.rows : []
  const sig = JSON.stringify({ rows: emittedRows, covers, hasSchedule })
  useEffect(() => {
    onChange(covers ? allocation.rows : [], covers, hasSchedule)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sig])

  const notFound = scheduleQuery.error instanceof ApiError && scheduleQuery.error.status === 404
  if (notFound) {
    return (
      <p className="nx-field__error" role="alert">
        Este contrato de ejecución requiere un plan de pagos antes de poder pagar cuotas. Créalo desde
        la ficha del contrato en el proyecto.
      </p>
    )
  }
  if (scheduleQuery.isLoading) return <LoadingState label="Cargando contexto contractual…" />

  const columns: TableColumn<ContractInstallment>[] = [
    {
      key: 'kind',
      header: 'Tipo',
      render: (r) => (
        <Badge tone={r.installmentKind === 'ADVANCE' ? 'info' : 'neutral'}>
          {r.installmentKind === 'REGULAR'
            ? `Cuota ${r.regularNumber} de ${r.regularCount}`
            : contractInstallmentKindLabel(r.installmentKind)}
        </Badge>
      ),
    },
    { key: 'due', header: 'Vencimiento', render: (r) => r.dueDate },
    { key: 'sched', header: 'Programado', numeric: true, render: (r) => formatMoney(r.scheduledAmount, currency) },
    { key: 'ret', header: 'Retención', numeric: true, render: (r) => (Number(r.retentionAmount) > 0 ? formatMoney(r.retentionAmount, currency) : '—') },
    { key: 'net', header: 'Neto', numeric: true, render: (r) => formatMoney(r.netDue, currency) },
    { key: 'paid', header: 'Pagado', numeric: true, render: (r) => formatMoney(r.paid, currency) },
    { key: 'rem', header: 'Pendiente', numeric: true, render: (r) => formatMoney(r.remaining, currency) },
    {
      key: 'status',
      header: 'Estado',
      render: (r) => <Badge tone={STATUS_TONE[r.status] ?? 'neutral'}>{contractInstallmentStatusLabel(r.status)}</Badge>,
    },
    {
      key: 'pick',
      header: '',
      render: (r) =>
        r.status === 'PAID' || r.status === 'CANCELLED' ? null : (
          <Button
            variant={r.installmentId === primaryId ? 'secondary' : 'ghost'}
            onClick={() => setManualId(r.installmentId)}
          >
            {r.installmentId === primaryId ? 'Seleccionada' : 'Aplicar a esta'}
          </Button>
        ),
    },
  ]

  const s = summaryQuery.data
  return (
    <div className="nx-contract-context">
      <p className="nx-field__label">{beneficiaryVerb}</p>
      <dl className="nx-voucher-preview">
        {contract ? (
          <>
            <div><dt>Contrato</dt><dd>{contract.contractNumber}</dd></div>
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
            <div><dt>Anticipo programado</dt><dd>{formatMoney(s.advanceScheduled, currency)}</dd></div>
            <div><dt>Anticipo pagado</dt><dd>{formatMoney(s.advancePaid, currency)}</dd></div>
            <div><dt>Pagado acumulado</dt><dd>{formatMoney(s.paidAccumulated, currency)}</dd></div>
            <div><dt>Saldo contractual</dt><dd>{formatMoney(s.contractBalance, currency)}</dd></div>
          </>
        ) : null}
      </dl>

      <p className="nx-field__label">Cuotas del plan</p>
      <div style={{ overflowX: 'auto' }}>
        <Table
          columns={columns}
          rows={installments}
          getRowKey={(r) => r.installmentId}
          emptyMessage="El plan no tiene cuotas."
        />
      </div>

      {amount != null && amount > 0 ? (
        <div className="nx-contract-context__fifo" role="status">
          {covers ? (
            <>
              <p className="nx-field__label">Asignación del pago</p>
              <ul className="nx-contract-context__alloc">
                {allocation.rows.map((r) => {
                  const i = installments.find((x) => x.installmentId === r.installmentId)
                  return (
                    <li key={r.installmentId}>
                      {i?.installmentKind === 'REGULAR'
                        ? `Cuota ${i.regularNumber} de ${i.regularCount}`
                        : contractInstallmentKindLabel(i?.installmentKind ?? 'REGULAR')}{' '}
                      ({i?.dueDate}) ← {formatMoney(r.amountApplied, currency)}
                    </li>
                  )
                })}
              </ul>
            </>
          ) : (
            <p className="nx-field__error" role="alert">
              No se puede confirmar el pago porque el monto ({formatMoney(amount, currency)}) no
              puede asignarse íntegramente al plan contractual (asignable{' '}
              {formatMoney(allocation.total, currency)}). Revisa el plan o el monto.
            </p>
          )}
        </div>
      ) : null}
    </div>
  )
}
