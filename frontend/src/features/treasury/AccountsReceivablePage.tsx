import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  CustomerSelector,
  EmptyState,
  LoadingState,
  Modal,
  MoneyInput,
  Select,
  Table,
  type TableColumn,
} from '../../design-system'
import { crmService } from '../../services/crmService'
import { masterDataService } from '../../services/masterDataService'
import { treasuryService } from '../../services/treasuryService'
import { useMutationError } from '../../hooks/useMutationError'
import { arService, type CustomerInvoice } from '../../services/apArService'
import { formatMoney } from '../../utils/currency'
import './TreasuryPage.css'

export function AccountsReceivablePage() {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [openCreate, setOpenCreate] = useState(false)

  const companiesQuery = useQuery({
    queryKey: ['master-data', 'companies'],
    queryFn: masterDataService.listCompanies,
  })
  const companies = companiesQuery.data ?? []
  const activeCompanyId = companyId ?? companies[0]?.id ?? null

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
  const invoicesQuery = useQuery({
    queryKey: ['ar', 'customer-invoices', activeCompanyId],
    queryFn: () => arService.listInvoices(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const customersQuery = useQuery({
    queryKey: ['crm', 'customers', activeCompanyId],
    queryFn: () => crmService.listCustomers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const approve = useMutation({
    mutationFn: (id: string) => arService.approveInvoice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ar', 'customer-invoices', activeCompanyId] })
    },
    onError: (error) => handleMutationError(error, 'Aprobar factura de cliente'),
  })

  if (companiesQuery.isLoading) return <LoadingState label="Cargando…" />
  if (companies.length === 0) {
    return (
      <EmptyState
        icon="receipt"
        title="Aún no hay compañías configuradas"
        description="Crea una compañía desde Tesorería antes de registrar facturas de cliente."
      />
    )
  }

  const revenueAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'REVENUE')
  const receivableAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'ASSET')
  const treasuryAccounts = treasuryAccountsQuery.data ?? []
  const invoices = invoicesQuery.data ?? []
  const customers = customersQuery.data ?? []
  const customerNameById = new Map(customers.map((c) => [c.id, c.legalName]))

  const columns: TableColumn<CustomerInvoice>[] = [
    { key: 'invoiceNumber', header: 'Factura', render: (row) => row.invoiceNumber },
    {
      key: 'customerId',
      header: 'Cliente',
      render: (row) => customerNameById.get(row.customerId) ?? row.customerId,
    },
    {
      key: 'amount',
      header: 'Monto',
      render: (row) => formatMoney(row.amount, row.currencyCode),
    },
    { key: 'amountCollected', header: 'Cobrado', render: (row) => formatMoney(row.amountCollected, row.currencyCode) },
    { key: 'status', header: 'Estado', render: (row) => row.status },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <div className="nx-treasury__actions">
          {row.status === 'DRAFT' ? (
            <Button
              variant="secondary"
              onClick={() => approve.mutate(row.id)}
              loading={approve.isPending}
            >
              Aprobar
            </Button>
          ) : null}
          {['APPROVED', 'PARTIALLY_COLLECTED'].includes(row.status) &&
          treasuryAccounts.length > 0 ? (
            <CollectButton
              invoiceId={row.id}
              treasuryAccountId={treasuryAccounts[0].id}
              remaining={row.amount - row.amountCollected}
            />
          ) : null}
        </div>
      ),
    },
  ]

  return (
    <div className="nx-treasury">
      <header className="nx-treasury__header">
        <h1 className="nx-dashboard__title">Cuentas por cobrar</h1>
        <Select
          value={activeCompanyId ?? ''}
          onChange={(e) => setCompanyId(e.target.value)}
          aria-label="Compañía"
        >
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </Select>
      </header>

      <Card title="Acciones">
        <Button
          variant="secondary"
          onClick={() => setOpenCreate(true)}
          disabled={
            revenueAccounts.length === 0 || receivableAccounts.length === 0 || customers.length === 0
          }
        >
          Registrar factura de cliente
        </Button>
        {revenueAccounts.length === 0 || receivableAccounts.length === 0 ? (
          <p className="nx-field__error">
            Necesitas al menos una cuenta REVENUE y una ASSET (cuentas por cobrar) en el catálogo
            contable.
          </p>
        ) : null}
        {customers.length === 0 ? (
          <p className="nx-field__error">
            Necesitas al menos un cliente registrado (Comercial → Clientes).
          </p>
        ) : null}
      </Card>

      <Table
        columns={columns}
        rows={invoices}
        getRowKey={(row) => row.id}
        emptyMessage="Aún no hay facturas de cliente registradas."
      />

      {openCreate && activeCompanyId ? (
        <CreateCustomerInvoiceModal
          companyId={activeCompanyId}
          revenueAccounts={revenueAccounts}
          receivableAccounts={receivableAccounts}
          customers={customers}
          onClose={() => setOpenCreate(false)}
          onCreated={() =>
            queryClient.invalidateQueries({
              queryKey: ['ar', 'customer-invoices', activeCompanyId],
            })
          }
        />
      ) : null}
    </div>
  )
}

function CreateCustomerInvoiceModal({
  companyId,
  revenueAccounts,
  receivableAccounts,
  customers,
  onClose,
  onCreated,
}: {
  companyId: string
  revenueAccounts: { id: string; name: string }[]
  receivableAccounts: { id: string; name: string }[]
  customers: { id: string; legalName: string }[]
  onClose: () => void
  onCreated: (invoice: CustomerInvoice) => void
}) {
  const [customerId, setCustomerId] = useState<string | null>(null)
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [amount, setAmount] = useState<number | null>(null)
  const [revenueAccountId, setRevenueAccountId] = useState(revenueAccounts[0]?.id ?? '')
  const [receivableAccountId, setReceivableAccountId] = useState(receivableAccounts[0]?.id ?? '')
  const handleMutationError = useMutationError()

  const customerOptions = customers.map((c) => ({ id: c.id, label: c.legalName }))

  const mutation = useMutation({
    mutationFn: () =>
      arService.createInvoice({
        companyId,
        customerId,
        invoiceNumber,
        scope: 'GENERAL',
        revenueAccountId,
        receivableAccountId,
        currencyCode: 'HNL',
        amount: String(amount ?? 0),
        invoiceDate: new Date().toISOString().slice(0, 10),
        dueDate: new Date().toISOString().slice(0, 10),
      }) as Promise<CustomerInvoice>,
    onSuccess: (invoice) => {
      onCreated(invoice)
      onClose()
    },
    onError: (error) => handleMutationError(error, 'Registrar factura de cliente'),
  })

  return (
    <Modal open title="Registrar factura de cliente" onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <CustomerSelector options={customerOptions} value={customerId} onChange={setCustomerId} />
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
        <MoneyInput label="Monto" value={amount} onChange={setAmount} />
        {mutation.isError ? (
          <p className="nx-field__error">{(mutation.error as Error).message}</p>
        ) : null}
        <Button
          type="submit"
          loading={mutation.isPending}
          disabled={!amount || !customerId || !invoiceNumber}
        >
          Registrar
        </Button>
      </form>
    </Modal>
  )
}

function CollectButton({
  invoiceId,
  treasuryAccountId,
  remaining,
}: {
  invoiceId: string
  treasuryAccountId: string
  remaining: number
}) {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const mutation = useMutation({
    mutationFn: async ({
      payload,
      idempotencyKey,
    }: {
      payload: Record<string, unknown>
      idempotencyKey: string
    }) => {
      await arService.collect(invoiceId, payload, idempotencyKey)
      return arService.getInvoice(invoiceId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ar', 'customer-invoices'] })
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
    },
    onError: (error) => handleMutationError(error, 'Cobrar factura de cliente'),
  })

  return (
    <Button
      variant="ghost"
      loading={mutation.isPending}
      onClick={() =>
        mutation.mutate({
          payload: {
            treasuryAccountId,
            amount: String(remaining),
            receiptDate: new Date().toISOString().slice(0, 10),
          },
          idempotencyKey: crypto.randomUUID(),
        })
      }
    >
      Cobrar saldo ({remaining.toFixed(2)})
    </Button>
  )
}
