import { useQuery } from '@tanstack/react-query'
import {
  Badge,
  Card,
  CompanySelector,
  EmptyState,
  ErrorState,
  LoadingState,
  StatCard,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import {
  contractPaymentService,
  type ContractInstallment,
  type ContractLedgerEntry,
  type LedgerAllocation,
} from '../../services/contractPaymentService'
import { formatMoney } from '../../utils/currency'

const STATUS_TONE: Record<string, 'success' | 'warning' | 'danger' | 'neutral'> = {
  PAID: 'success',
  PARTIALLY_PAID: 'warning',
  DUE: 'warning',
  OVERDUE: 'danger',
  UPCOMING: 'neutral',
  CANCELLED: 'neutral',
}

export function ContractPaymentLedgerPage() {
  const { companies, activeCompanyId, activeCompany, setActiveCompanyId, isLoading, isError, refetch } =
    useActiveCompany()
  const currency = activeCompany?.functionalCurrencyCode ?? undefined

  const query = useQuery({
    queryKey: ['contract-payment-ledger', activeCompanyId],
    queryFn: () => contractPaymentService.ledger(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return (
      <EmptyState
        icon="book"
        title="Configura una compañía primero"
        description="El libro contractual de pagos necesita una compañía."
      />
    )
  }

  const installmentColumns: TableColumn<ContractInstallment>[] = [
    { key: 'sequence', header: '#', render: (row) => row.sequence },
    { key: 'periodLabel', header: 'Período contractual', render: (row) => row.periodLabel },
    { key: 'dueDate', header: 'Vence', render: (row) => row.dueDate },
    { key: 'netDue', header: 'Neto', render: (row) => formatMoney(row.netDue, currency) },
    { key: 'paid', header: 'Pagado', render: (row) => formatMoney(row.paid, currency) },
    { key: 'remaining', header: 'Saldo', render: (row) => formatMoney(row.remaining, currency) },
    {
      key: 'status',
      header: 'Estado',
      render: (row) => <Badge tone={STATUS_TONE[row.status] ?? 'neutral'}>{row.status}</Badge>,
    },
  ]

  const allocationColumns: TableColumn<LedgerAllocation>[] = [
    { key: 'paymentDate', header: 'Fecha de pago', render: (row) => row.paymentDate },
    { key: 'installmentPeriodLabel', header: 'Cuota liquidada', render: (row) => row.installmentPeriodLabel },
    { key: 'amountApplied', header: 'Importe aplicado', render: (row) => formatMoney(row.amountApplied, currency) },
    {
      key: 'bankTransactionReference',
      header: 'Referencia bancaria',
      render: (row) => row.bankTransactionReference ?? '—',
    },
    {
      key: 'reversed',
      header: 'Estado',
      render: (row) => (
        <Badge tone={row.reversed ? 'danger' : 'success'}>{row.reversed ? 'Reversado' : 'Vigente'}</Badge>
      ),
    },
  ]

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <p className="nx-page__eyebrow">Finanzas</p>
          <h1 className="nx-dashboard__title">Libro contractual de pagos</h1>
          <p className="nx-field__hint">
            Por cada contrato con plan de pagos: sus cuotas con estado real y las asignaciones de pago que
            las liquidaron. El período contractual es independiente de la fecha de pago y del período
            contable.
          </p>
        </div>
        <CompanySelector
          options={companies.map((company) => ({ id: company.id, label: company.name }))}
          value={activeCompanyId}
          onChange={setActiveCompanyId}
        />
      </header>

      {query.isLoading ? (
        <LoadingState label="Cargando libro contractual…" />
      ) : query.isError ? (
        <ErrorState description="No se pudo cargar el libro contractual." onRetry={() => query.refetch()} />
      ) : query.data ? (
        query.data.entries.length === 0 ? (
          <EmptyState
            icon="book"
            title="Sin contratos con plan de pagos"
            description="Crea un plan de pagos para un contrato de proveedor para verlo aquí."
          />
        ) : (
          <>
            <div className="nx-stat-grid">
              <StatCard
                label="Valor contractual total"
                value={formatMoney(query.data.totalContractValue, currency)}
              />
              <StatCard
                label="Pagado acumulado"
                value={formatMoney(query.data.totalPaidAccumulated, currency)}
              />
              <StatCard
                label="Saldo contractual pendiente"
                value={formatMoney(query.data.totalContractBalance, currency)}
              />
            </div>

            {query.data.entries.map((entry: ContractLedgerEntry) => (
              <Card key={entry.scheduleId}>
                <header className="nx-page__header">
                  <div>
                    <h2 className="nx-dashboard__subtitle">
                      {entry.contractNumber}
                      {entry.supplierLegalName ? ` · ${entry.supplierLegalName}` : ''}
                    </h2>
                    <p className="nx-field__hint">
                      Valor {formatMoney(entry.contractValue, entry.currencyCode)} · Pagado{' '}
                      {formatMoney(entry.paidAccumulated, entry.currencyCode)} · Saldo{' '}
                      {formatMoney(entry.contractBalance, entry.currencyCode)}
                      {Number(entry.overdueBalance) > 0
                        ? ` · Vencido ${formatMoney(entry.overdueBalance, entry.currencyCode)}`
                        : ''}
                    </p>
                  </div>
                </header>

                <h3 className="nx-field__label">Cuotas</h3>
                <Table
                  columns={installmentColumns}
                  rows={entry.installments}
                  getRowKey={(row) => row.installmentId}
                  emptyMessage="Sin cuotas."
                />

                <h3 className="nx-field__label">Asignaciones de pago</h3>
                <Table
                  columns={allocationColumns}
                  rows={entry.allocations}
                  getRowKey={(row) => `${row.paymentId}-${row.installmentSequence}`}
                  emptyMessage="Todavía no se ha aplicado ningún pago a este contrato."
                />
              </Card>
            ))}
          </>
        )
      ) : null}
    </div>
  )
}
