import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  EmptyState,
  LoadingState,
  Modal,
  MoneyInput,
  Select,
  Table,
  type TableColumn,
} from '../../design-system'
import { masterDataService } from '../../services/masterDataService'
import { treasuryService } from '../../services/treasuryService'
import { apService, type SupplierInvoice } from '../../services/apArService'
import './TreasuryPage.css'

export function AccountsPayablePage() {
  const queryClient = useQueryClient()
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
    queryKey: ['ap', 'supplier-invoices', activeCompanyId],
    queryFn: () => apService.listInvoices(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const approve = useMutation({
    mutationFn: (id: string) => apService.approveInvoice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-invoices', activeCompanyId] })
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
    },
  })

  if (companiesQuery.isLoading) return <LoadingState label="Cargando…" />
  if (companies.length === 0) {
    return (
      <EmptyState
        icon="💳"
        title="Aún no hay compañías configuradas"
        description="Crea una compañía desde Tesorería antes de registrar facturas de proveedor."
      />
    )
  }

  const expenseAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'EXPENSE')
  const payableAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'LIABILITY')
  const treasuryAccounts = treasuryAccountsQuery.data ?? []
  const invoices = invoicesQuery.data ?? []

  const columns: TableColumn<SupplierInvoice>[] = [
    { key: 'invoiceNumber', header: 'Factura', render: (row) => row.invoiceNumber },
    { key: 'supplierName', header: 'Proveedor', render: (row) => row.supplierName },
    {
      key: 'amount',
      header: 'Monto',
      render: (row) => `${row.currencyCode} ${row.amount.toFixed(2)}`,
    },
    { key: 'amountPaid', header: 'Pagado', render: (row) => row.amountPaid.toFixed(2) },
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
          {['APPROVED', 'SCHEDULED', 'PARTIALLY_PAID'].includes(row.status) &&
          treasuryAccounts.length > 0 ? (
            <PaySupplierInvoiceButton
              invoiceId={row.id}
              treasuryAccountId={treasuryAccounts[0].id}
              remaining={row.amount + row.taxAmount - row.amountPaid}
            />
          ) : null}
        </div>
      ),
    },
  ]

  return (
    <div className="nx-treasury">
      <header className="nx-treasury__header">
        <h1 className="nx-dashboard__title">Cuentas por pagar</h1>
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
          disabled={expenseAccounts.length === 0 || payableAccounts.length === 0}
        >
          Registrar factura de proveedor
        </Button>
        {expenseAccounts.length === 0 || payableAccounts.length === 0 ? (
          <p className="nx-field__error">
            Necesitas al menos una cuenta EXPENSE y una LIABILITY en el catálogo contable.
          </p>
        ) : null}
      </Card>

      <Table
        columns={columns}
        rows={invoices}
        getRowKey={(row) => row.id}
        emptyMessage="Aún no hay facturas de proveedor registradas."
      />

      {openCreate && activeCompanyId ? (
        <CreateSupplierInvoiceModal
          companyId={activeCompanyId}
          expenseAccounts={expenseAccounts}
          payableAccounts={payableAccounts}
          onClose={() => setOpenCreate(false)}
          onCreated={() =>
            queryClient.invalidateQueries({
              queryKey: ['ap', 'supplier-invoices', activeCompanyId],
            })
          }
        />
      ) : null}
    </div>
  )
}

function CreateSupplierInvoiceModal({
  companyId,
  expenseAccounts,
  payableAccounts,
  onClose,
  onCreated,
}: {
  companyId: string
  expenseAccounts: { id: string; name: string }[]
  payableAccounts: { id: string; name: string }[]
  onClose: () => void
  onCreated: (invoice: SupplierInvoice) => void
}) {
  const [supplierName, setSupplierName] = useState('')
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [amount, setAmount] = useState<number | null>(null)
  const [expenseAccountId, setExpenseAccountId] = useState(expenseAccounts[0]?.id ?? '')
  const [payableAccountId, setPayableAccountId] = useState(payableAccounts[0]?.id ?? '')

  const mutation = useMutation({
    mutationFn: () =>
      apService.createInvoice({
        companyId,
        supplierName,
        invoiceNumber,
        scope: 'GENERAL',
        expenseAccountId,
        payableAccountId,
        currencyCode: 'HNL',
        amount: String(amount ?? 0),
        invoiceDate: new Date().toISOString().slice(0, 10),
        dueDate: new Date().toISOString().slice(0, 10),
      }) as Promise<SupplierInvoice>,
    onSuccess: (invoice) => {
      onCreated(invoice)
      onClose()
    },
  })

  return (
    <Modal open title="Registrar factura de proveedor" onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <label className="nx-field">
          <span className="nx-field__label">Proveedor</span>
          <input
            className="nx-input"
            value={supplierName}
            onChange={(e) => setSupplierName(e.target.value)}
            required
          />
        </label>
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
          label="Cuenta de gasto"
          value={expenseAccountId}
          onChange={(e) => setExpenseAccountId(e.target.value)}
        >
          {expenseAccounts.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </Select>
        <Select
          label="Cuenta por pagar"
          value={payableAccountId}
          onChange={(e) => setPayableAccountId(e.target.value)}
        >
          {payableAccounts.map((a) => (
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
          disabled={!amount || !supplierName || !invoiceNumber}
        >
          Registrar
        </Button>
      </form>
    </Modal>
  )
}

function PaySupplierInvoiceButton({
  invoiceId,
  treasuryAccountId,
  remaining,
}: {
  invoiceId: string
  treasuryAccountId: string
  remaining: number
}) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: async () => {
      await apService.pay(invoiceId, {
        treasuryAccountId,
        amount: String(remaining),
        paymentDate: new Date().toISOString().slice(0, 10),
      })
      return apService.getInvoice(invoiceId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-invoices'] })
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
    },
  })

  return (
    <Button variant="ghost" loading={mutation.isPending} onClick={() => mutation.mutate()}>
      Pagar saldo ({remaining.toFixed(2)})
    </Button>
  )
}
