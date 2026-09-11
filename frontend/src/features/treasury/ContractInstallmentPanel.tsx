import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Badge, Button, LoadingState, Table, type TableColumn } from '../../design-system'
import {
  contractPaymentService,
  type ContractInstallment,
} from '../../services/contractPaymentService'
import { ApiError } from '../../services/httpClient'
import { procurementService } from '../../services/procurementService'
import { SUPPLIER_CONTRACT_CATEGORY_LABELS } from '../../types/procurement'
import { formatMoney } from '../../utils/currency'
import {
  contractInstallmentKindLabel,
  contractInstallmentStatusLabel,
} from '../../utils/statusLabels'

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

function toCents(value: string | number): bigint {
  const raw = typeof value === 'number' ? value.toFixed(2) : String(value).trim()
  const match = raw.match(/^([+-]?)(\d+)(?:\.(\d+))?$/)
  if (!match) return 0n
  const fraction = (match[3] ?? '').padEnd(3, '0')
  let cents = BigInt(match[2]) * 100n + BigInt(fraction.slice(0, 2) || '0')
  if (Number(fraction[2] ?? '0') >= 5) cents += 1n
  return match[1] === '-' ? -cents : cents
}

function fromCents(cents: bigint): string {
  const negative = cents < 0n
  const abs = negative ? -cents : cents
  return `${negative ? '-' : ''}${abs / 100n}.${String(abs % 100n).padStart(2, '0')}`
}

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
  const currency = scheduleQuery.data?.currencyCode ?? null
  const [manualId, setManualId] = useState<string>('')

  const summaryQuery = useQuery({
    queryKey: ['contract-payments', 'summary', scheduleId, asOf],
    queryFn: () => contractPaymentService.summary(scheduleId as string, asOf),
    enabled: Boolean(scheduleId && asOf),
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
  const contract = (contractsQuery.data ?? []).find((item) => item.id === supplierContractId)
  const party = (suppliersQuery.data ?? []).find((item) => item.id === contract?.supplierId)
  const beneficiaryVerb = useMemo(() => {
    const role = party?.partyRole
    if (role === 'CONTRACTOR') return 'Registrar pago a contratista'
    if (role === 'BOTH') return 'Registrar pago'
    return 'Registrar pago a proveedor'
  }, [party?.partyRole])

  const installments = useMemo(() => scheduleQuery.data?.installments ?? [], [scheduleQuery.data])
  const primaryId = manualId || selectedInstallmentId || ''

  // Primary installment first, then FIFO. All arithmetic is exact integer cents;
  // no binary float is used to compare scheduled/remaining/payment amounts.
  const allocation = useMemo(() => {
    const amountCents = amount == null ? 0n : toCents(amount)
    if (amountCents <= 0n) return { rows: [] as ContractAllocationDraft[], totalCents: 0n }
    let left = amountCents
    const ordered = [
      ...installments.filter((item) => item.installmentId === primaryId),
      ...installments.filter((item) => item.installmentId !== primaryId),
    ]
    const rows: ContractAllocationDraft[] = []
    for (const installment of ordered) {
      if (left <= 0n) break
      if (['CANCELLED', 'PAID', 'UPCOMING'].includes(installment.status)) continue
      const remainingCents = toCents(installment.remaining)
      if (remainingCents <= 0n) continue
      const applied = left < remainingCents ? left : remainingCents
      rows.push({ installmentId: installment.installmentId, amountApplied: fromCents(applied) })
      left -= applied
    }
    return { rows, totalCents: amountCents - left }
  }, [amount, installments, primaryId])

  const amountCents = amount == null ? 0n : toCents(amount)
  const covers = amountCents > 0n && allocation.totalCents === amountCents
  const hasSchedule = Boolean(scheduleId)
  const emittedRows = covers ? allocation.rows : []
  const sig = JSON.stringify({ rows: emittedRows, covers, hasSchedule })
  useEffect(() => {
    onChange(covers ? allocation.rows : [], covers, hasSchedule)
    // The signature captures all business output; parent callback identity is intentionally excluded.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sig])

  const notFound = scheduleQuery.error instanceof ApiError && scheduleQuery.error.status === 404
  if (notFound) {
    return (
      <p className="nx-field__error" role="alert">
        Este contrato requiere un plan de pagos antes de pagar cuotas. Créalo desde la ficha del
        contrato en el proyecto.
      </p>
    )
  }
  if (scheduleQuery.isLoading) return <LoadingState label="Cargando contexto contractual…" />
  if (!currency) {
    return (
      <p className="nx-field__error" role="alert">
        El plan contractual no tiene una moneda válida. Corrige el contrato antes de registrar un
        pago.
      </p>
    )
  }

  const columns: TableColumn<ContractInstallment>[] = [
    {
      key: 'kind',
      header: 'Tipo',
      render: (row) => (
        <Badge tone={row.installmentKind === 'ADVANCE' ? 'info' : 'neutral'}>
          {row.installmentKind === 'REGULAR'
            ? `Cuota ${row.regularNumber} de ${row.regularCount}`
            : contractInstallmentKindLabel(row.installmentKind)}
        </Badge>
      ),
    },
    { key: 'due', header: 'Vencimiento', render: (row) => row.dueDate },
    {
      key: 'sched',
      header: 'Programado',
      numeric: true,
      render: (row) => formatMoney(row.scheduledAmount, currency),
    },
    {
      key: 'ret',
      header: 'Retención',
      numeric: true,
      render: (row) =>
        toCents(row.retentionAmount) > 0n ? formatMoney(row.retentionAmount, currency) : '—',
    },
    {
      key: 'net',
      header: 'Neto',
      numeric: true,
      render: (row) => formatMoney(row.netDue, currency),
    },
    {
      key: 'paid',
      header: 'Pagado',
      numeric: true,
      render: (row) => formatMoney(row.paid, currency),
    },
    {
      key: 'rem',
      header: 'Pendiente',
      numeric: true,
      render: (row) => formatMoney(row.remaining, currency),
    },
    {
      key: 'status',
      header: 'Estado',
      render: (row) => (
        <Badge tone={STATUS_TONE[row.status] ?? 'neutral'}>
          {contractInstallmentStatusLabel(row.status)}
        </Badge>
      ),
    },
    {
      key: 'pick',
      header: '',
      render: (row) =>
        ['PAID', 'CANCELLED', 'UPCOMING'].includes(row.status) ? (
          row.status === 'UPCOMING' ? (
            <span className="nx-field__hint">Disponible para pago en {row.periodLabel}</span>
          ) : null
        ) : (
          <Button
            variant={row.installmentId === primaryId ? 'secondary' : 'ghost'}
            onClick={() => setManualId(row.installmentId)}
          >
            {row.installmentId === primaryId ? 'Seleccionada' : 'Aplicar a esta'}
          </Button>
        ),
    },
  ]

  const summary = summaryQuery.data
  return (
    <div className="nx-contract-context">
      <p className="nx-field__label">{beneficiaryVerb}</p>
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
        {summary ? (
          <>
            <div>
              <dt>Valor contractual</dt>
              <dd>{formatMoney(summary.contractValue, currency)}</dd>
            </div>
            <div>
              <dt>Anticipo programado</dt>
              <dd>{formatMoney(summary.advanceScheduled, currency)}</dd>
            </div>
            <div>
              <dt>Anticipo pagado</dt>
              <dd>{formatMoney(summary.advancePaid, currency)}</dd>
            </div>
            <div>
              <dt>Pagado acumulado</dt>
              <dd>{formatMoney(summary.paidAccumulated, currency)}</dd>
            </div>
            <div>
              <dt>Saldo contractual</dt>
              <dd>{formatMoney(summary.contractBalance, currency)}</dd>
            </div>
          </>
        ) : null}
      </dl>

      <p className="nx-field__label">Cuotas del plan · referencia contractual {asOf}</p>
      <div style={{ overflowX: 'auto' }}>
        <Table
          columns={columns}
          rows={installments}
          getRowKey={(row) => row.installmentId}
          emptyMessage="El plan no tiene cuotas."
        />
      </div>

      {amountCents > 0n ? (
        <div className="nx-contract-context__fifo" role="status">
          {covers ? (
            <>
              <p className="nx-field__label">Asignación del pago</p>
              <ul className="nx-contract-context__alloc">
                {allocation.rows.map((row) => {
                  const installment = installments.find(
                    (item) => item.installmentId === row.installmentId,
                  )
                  return (
                    <li key={row.installmentId}>
                      {installment?.installmentKind === 'REGULAR'
                        ? `Cuota ${installment.regularNumber} de ${installment.regularCount}`
                        : contractInstallmentKindLabel(installment?.installmentKind ?? 'REGULAR')}{' '}
                      ({installment?.dueDate}) ← {formatMoney(row.amountApplied, currency)}
                    </li>
                  )
                })}
              </ul>
            </>
          ) : (
            <p className="nx-field__error" role="alert">
              No se puede confirmar el pago porque {formatMoney(fromCents(amountCents), currency)} no
              puede asignarse íntegramente al plan. Asignable:{' '}
              {formatMoney(fromCents(allocation.totalCents), currency)}.
            </p>
          )}
        </div>
      ) : null}
    </div>
  )
}
