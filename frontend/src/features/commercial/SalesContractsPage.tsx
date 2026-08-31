import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Badge, Button, Card, EmptyState, ErrorState, LoadingState, Modal, Select, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { crmService } from '../../services/crmService'
import { masterDataService } from '../../services/masterDataService'
import type { SalesContract } from '../../types/crm'
import { formatMoney } from '../../utils/currency'

export function SalesContractsPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const [billingContract, setBillingContract] = useState<SalesContract | null>(null)
  const queryClient = useQueryClient()

  const contractsQuery = useQuery({
    queryKey: ['crm', 'sales-contracts', activeCompanyId],
    queryFn: () => crmService.listSalesContracts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const accountsQuery = useQuery({
    queryKey: ['master-data', 'accounts', activeCompanyId],
    queryFn: () => masterDataService.listAccounts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['crm', 'sales-contracts', activeCompanyId] })
    queryClient.invalidateQueries({ queryKey: ['ar', 'customer-invoices', activeCompanyId] })
  }

  const revenueAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'REVENUE')
  const receivableAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'ASSET')

  const columns: TableColumn<SalesContract>[] = [
    { key: 'contractNumber', header: 'Contrato', render: (row) => row.contractNumber },
    { key: 'amount', header: 'Monto', render: (row) => formatMoney(row.amount, row.currencyCode), numeric: true },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{row.status}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) =>
        row.status === 'ACTIVE' ? (
          <Button
            variant="secondary"
            disabled={revenueAccounts.length === 0 || receivableAccounts.length === 0}
            onClick={() => setBillingContract(row)}
          >
            Facturar
          </Button>
        ) : row.status === 'BILLED' ? (
          <span className="nx-field__hint">Facturado (AR #{row.customerInvoiceId?.slice(0, 8)})</span>
        ) : null,
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return <EmptyState title="Configura una compañía primero" description="No hay compañías registradas todavía." />
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Contratos de venta</h1>
      </header>

      {revenueAccounts.length === 0 || receivableAccounts.length === 0 ? (
        <p className="nx-field__error">
          Necesitas al menos una cuenta REVENUE y una ASSET (cuentas por cobrar) para poder facturar.
        </p>
      ) : null}

      <Card>
        {contractsQuery.isLoading ? (
          <LoadingState label="Cargando contratos…" />
        ) : contractsQuery.isError ? (
          <ErrorState onRetry={() => contractsQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={contractsQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay contratos de venta. Se crean al convertir una cotización aceptada."
          />
        )}
      </Card>

      {billingContract ? (
        <BillSalesContractModal
          contract={billingContract}
          revenueAccounts={revenueAccounts}
          receivableAccounts={receivableAccounts}
          onClose={() => setBillingContract(null)}
          onBilled={invalidate}
        />
      ) : null}
    </div>
  )
}

function BillSalesContractModal({
  contract,
  revenueAccounts,
  receivableAccounts,
  onClose,
  onBilled,
}: {
  contract: SalesContract
  revenueAccounts: { id: string; name: string }[]
  receivableAccounts: { id: string; name: string }[]
  onClose: () => void
  onBilled: () => void
}) {
  const [invoiceNumber, setInvoiceNumber] = useState(`CI-${contract.contractNumber}`)
  const [revenueAccountId, setRevenueAccountId] = useState(revenueAccounts[0]?.id ?? '')
  const [receivableAccountId, setReceivableAccountId] = useState(receivableAccounts[0]?.id ?? '')

  const mutation = useMutation({
    mutationFn: () =>
      crmService.billSalesContract(contract.id, {
        invoiceNumber,
        invoiceDate: new Date().toISOString().slice(0, 10),
        dueDate: new Date().toISOString().slice(0, 10),
        revenueAccountId,
        receivableAccountId,
      }),
    onSuccess: () => {
      onBilled()
      onClose()
    },
  })

  return (
    <Modal open title={`Facturar contrato ${contract.contractNumber}`} onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <p className="nx-field__hint">
          Monto a facturar: {contract.currencyCode} {contract.amount}
        </p>
        <label className="nx-field">
          <span className="nx-field__label">Número de factura</span>
          <input
            className="nx-input"
            value={invoiceNumber}
            onChange={(e) => setInvoiceNumber(e.target.value)}
            required
          />
        </label>
        <Select
          label="Cuenta de ingreso"
          value={revenueAccountId}
          onChange={(e) => setRevenueAccountId(e.target.value)}
        >
          {revenueAccounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </Select>
        <Select
          label="Cuenta por cobrar"
          value={receivableAccountId}
          onChange={(e) => setReceivableAccountId(e.target.value)}
        >
          {receivableAccounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </Select>
        {mutation.isError ? (
          <p className="nx-field__error">{(mutation.error as Error).message}</p>
        ) : null}
        <Button type="submit" loading={mutation.isPending} disabled={!invoiceNumber}>
          Facturar (crea factura AR real)
        </Button>
      </form>
    </Modal>
  )
}
