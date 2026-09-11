import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
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
import { apService } from '../../services/apArService'
import {
  contractPaymentService,
  type ContractInstallment,
  type ContractLedgerEntry,
  type LedgerAllocation,
} from '../../services/contractPaymentService'
import { masterDataService } from '../../services/masterDataService'
import { procurementService } from '../../services/procurementService'
import { treasuryService } from '../../services/treasuryService'
import { formatMoney } from '../../utils/currency'
import {
  CreateSupplierInvoiceModal,
  PaySupplierInvoiceButton,
} from '../treasury/SupplierInvoiceFlows'

const STATUS_TONE: Record<string, 'success' | 'warning' | 'danger' | 'neutral'> = {
  PAID: 'success',
  PARTIALLY_PAID: 'warning',
  DUE: 'warning',
  OVERDUE: 'danger',
  UPCOMING: 'neutral',
  CANCELLED: 'neutral',
}

export function ContractPaymentLedgerPage() {
  const queryClient = useQueryClient()
  const [prepare, setPrepare] = useState<{
    entry: ContractLedgerEntry
    installment: ContractInstallment
  } | null>(null)
  const {
    companies,
    activeCompanyId,
    activeCompany,
    setActiveCompanyId,
    isLoading,
    isError,
    refetch,
  } = useActiveCompany()
  const currency = activeCompany?.functionalCurrencyCode ?? null

  const query = useQuery({
    queryKey: ['contract-payment-ledger', activeCompanyId],
    queryFn: () => contractPaymentService.ledger(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const invoicesQuery = useQuery({
    queryKey: ['ap', 'supplier-invoices', activeCompanyId],
    queryFn: () => apService.listInvoices(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const accountsQuery = useQuery({
    queryKey: ['master-data', 'accounts', activeCompanyId],
    queryFn: () => masterDataService.listAccounts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const treasuryAccountsQuery = useQuery({
    queryKey: ['treasury', 'accounts', activeCompanyId],
    queryFn: () => treasuryService.listAccounts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const contractsQuery = useQuery({
    queryKey: ['procurement', 'contracts', activeCompanyId],
    queryFn: () => procurementService.listContracts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const suppliersQuery = useQuery({
    queryKey: ['procurement', 'suppliers', activeCompanyId],
    queryFn: () => procurementService.listSuppliers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  if (isLoading) return <LoadingState label="Cargando compañías…" />
  if (isError) {
    return (
      <ErrorState
        description="No se pudieron cargar las compañías."
        onRetry={() => refetch()}
      />
    )
  }
  if (companies.length === 0) {
    return (
      <EmptyState
        icon="book"
        title="Configura una compañía primero"
        description="El libro contractual de pagos necesita una compañía."
      />
    )
  }
  if (!activeCompanyId || !activeCompany) {
    return (
      <div>
        <header className="nx-page__header">
          <div>
            <p className="nx-page__eyebrow">Finanzas</p>
            <h1 className="nx-dashboard__title">Libro contractual de pagos</h1>
          </div>
          <CompanySelector
            options={companies.map((company) => ({ id: company.id, label: company.name }))}
            value={activeCompanyId}
            onChange={setActiveCompanyId}
          />
        </header>
        <EmptyState
          icon="book"
          title="Selecciona una compañía"
          description="El libro contractual no mezcla importes entre compañías."
        />
      </div>
    )
  }
  if (!currency) {
    return (
      <EmptyState
        icon="warning"
        title="La compañía activa no tiene moneda funcional"
        description="Configura la moneda funcional antes de consultar el libro contractual."
      />
    )
  }

  const invoiceByInstallment = new Map(
    (invoicesQuery.data ?? [])
      .filter((invoice) => invoice.contractInstallmentId && invoice.status !== 'CANCELLED')
      .map((invoice) => [invoice.contractInstallmentId as string, invoice]),
  )

  const installmentColumns = (entry: ContractLedgerEntry): TableColumn<ContractInstallment>[] => [
    { key: 'sequence', header: '#', render: (row) => row.sequence },
    {
      key: 'periodLabel',
      header: 'Período contractual',
      render: (row) => row.periodLabel,
    },
    { key: 'dueDate', header: 'Vence', render: (row) => row.dueDate },
    { key: 'netDue', header: 'Neto', render: (row) => formatMoney(row.netDue, currency) },
    { key: 'paid', header: 'Pagado', render: (row) => formatMoney(row.paid, currency) },
    {
      key: 'remaining',
      header: 'Pendiente cuota',
      render: (row) => formatMoney(row.remaining, currency),
    },
    {
      key: 'contractBalanceAfter',
      header: 'Saldo contractual',
      render: (row) => formatMoney(row.contractBalanceAfter, currency),
    },
    {
      key: 'status',
      header: 'Estado',
      render: (row) => (
        <Badge tone={STATUS_TONE[row.status] ?? 'neutral'}>{statusLabel(row.status)}</Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Acción',
      render: (row) => {
        if (!row.payableNow) {
          return <span title={row.paymentBlockedReason ?? undefined}>Bloqueada</span>
        }
        const invoice = invoiceByInstallment.get(row.installmentId)
        if (invoice && ['APPROVED', 'SCHEDULED', 'PARTIALLY_PAID'].includes(invoice.status)) {
          const invoiceRemaining = invoice.amount + invoice.taxAmount - invoice.amountPaid
          return (
            <div className="nx-treasury__actions">
              <PaySupplierInvoiceButton
                invoice={invoice}
                companyId={activeCompanyId}
                treasuryAccounts={treasuryAccountsQuery.data ?? []}
                remaining={invoiceRemaining}
                selectedInstallmentId={row.installmentId}
                label={`Pagar ${row.periodLabel}`}
              />
              <PaySupplierInvoiceButton
                invoice={invoice}
                companyId={activeCompanyId}
                treasuryAccounts={treasuryAccountsQuery.data ?? []}
                remaining={invoiceRemaining}
                selectedInstallmentId={row.installmentId}
                label={`Liquidar ${row.periodLabel}`}
                lockAmount
              />
            </div>
          )
        }
        return (
          <div className="nx-treasury__actions">
            <Button variant="ghost" onClick={() => setPrepare({ entry, installment: row })}>
              Pagar {row.periodLabel}
            </Button>
            <Button variant="secondary" onClick={() => setPrepare({ entry, installment: row })}>
              Liquidar {row.periodLabel}
            </Button>
          </div>
        )
      },
    },
  ]

  const allocationColumns: TableColumn<LedgerAllocation>[] = [
    { key: 'paymentDate', header: 'Fecha económica', render: (row) => row.paymentDate },
    {
      key: 'sourceType',
      header: 'Origen',
      render: (row) =>
        row.sourceType === 'GENERAL_EXPENSE' ? 'Gasto general' : 'Pago a proveedor',
    },
    {
      key: 'installmentPeriodLabel',
      header: 'Cuota liquidada',
      render: (row) => row.installmentPeriodLabel,
    },
    {
      key: 'amountApplied',
      header: 'Importe aplicado',
      render: (row) => formatMoney(row.amountApplied, currency),
    },
    {
      key: 'bankTransactionReference',
      header: 'Referencia bancaria',
      render: (row) => row.bankTransactionReference ?? '—',
    },
    {
      key: 'reversed',
      header: 'Estado',
      render: (row) => (
        <Badge tone={row.reversed ? 'danger' : 'success'}>
          {row.reversed ? 'Reversado' : 'Vigente'}
        </Badge>
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
            Por cada contrato con plan de pagos: sus cuotas con estado real y las asignaciones de
            pago que las liquidaron. El período contractual es independiente de la fecha de pago y
            del período contable.
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
        <ErrorState
          description="No se pudo cargar el libro contractual."
          onRetry={() => query.refetch()}
        />
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
                  columns={installmentColumns(entry)}
                  rows={entry.installments}
                  getRowKey={(row) => row.installmentId}
                  emptyMessage="Sin cuotas."
                />

                <h3 className="nx-field__label">Asignaciones de pago</h3>
                <Table
                  columns={allocationColumns}
                  rows={entry.allocations}
                  getRowKey={(row) =>
                    `${row.sourceType}-${row.sourceId}-${row.installmentSequence}`
                  }
                  emptyMessage="Todavía no se ha aplicado ningún pago a este contrato."
                />
              </Card>
            ))}
          </>
        )
      ) : null}

      {prepare ? (
        <CreateSupplierInvoiceModal
          companyId={activeCompanyId}
          functionalCurrencyCode={currency}
          expenseAccounts={(accountsQuery.data ?? []).filter(
            (account) => account.accountType === 'EXPENSE' || account.accountType === 'ASSET',
          )}
          payableAccounts={(accountsQuery.data ?? []).filter(
            (account) => account.accountType === 'LIABILITY',
          )}
          suppliers={suppliersQuery.data ?? []}
          contracts={contractsQuery.data ?? []}
          initialContractId={prepare.entry.supplierContractId}
          lockedProjectId={prepare.entry.projectId ?? undefined}
          initialInstallment={{
            installmentId: prepare.installment.installmentId,
            remaining: prepare.installment.remaining,
            dueDate: prepare.installment.dueDate,
            periodLabel: prepare.installment.periodLabel,
          }}
          onClose={() => setPrepare(null)}
          onCreated={() => {
            setPrepare(null)
            queryClient.invalidateQueries({
              queryKey: ['ap', 'supplier-invoices', activeCompanyId],
            })
          }}
        />
      ) : null}
    </div>
  )
}

function statusLabel(status: string) {
  return (
    {
      PAID: 'Pagada',
      PARTIALLY_PAID: 'Parcialmente pagada',
      DUE: 'Vigente',
      OVERDUE: 'Vencida',
      UPCOMING: 'Próxima',
      CANCELLED: 'Cancelada',
    } as Record<string, string>
  )[status] ?? status
}
