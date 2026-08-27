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
  SupplierSelector,
  Table,
  type TableColumn,
} from '../../design-system'
import { useAuth } from '../auth/auth-context'
import { useCompanyUsers } from '../../hooks/useCompanyUsers'
import { useMutationError } from '../../hooks/useMutationError'
import { masterDataService } from '../../services/masterDataService'
import { procurementService } from '../../services/procurementService'
import { treasuryService } from '../../services/treasuryService'
import { apService, type SupplierInvoice } from '../../services/apArService'
import './TreasuryPage.css'

export function AccountsPayablePage() {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [openCreate, setOpenCreate] = useState(false)
  const [submitInvoiceId, setSubmitInvoiceId] = useState<string | null>(null)

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
  const suppliersQuery = useQuery({
    queryKey: ['procurement', 'suppliers', activeCompanyId],
    queryFn: () => procurementService.listSuppliers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const approve = useMutation({
    mutationFn: (id: string) => apService.approveInvoice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-invoices', activeCompanyId] })
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
    },
    onError: (error) => handleMutationError(error, 'Aprobar factura de proveedor'),
  })

  if (companiesQuery.isLoading) return <LoadingState label="Cargando…" />
  if (companies.length === 0) {
    return (
      <EmptyState
        icon="card"
        title="Aún no hay compañías configuradas"
        description="Crea una compañía desde Tesorería antes de registrar facturas de proveedor."
      />
    )
  }

  const expenseAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'EXPENSE')
  const payableAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'LIABILITY')
  const treasuryAccounts = treasuryAccountsQuery.data ?? []
  const invoices = invoicesQuery.data ?? []
  const suppliers = suppliersQuery.data ?? []
  const supplierNameById = new Map(suppliers.map((s) => [s.id, s.legalName]))

  const columns: TableColumn<SupplierInvoice>[] = [
    { key: 'invoiceNumber', header: 'Factura', render: (row) => row.invoiceNumber },
    {
      key: 'supplierId',
      header: 'Proveedor',
      render: (row) => supplierNameById.get(row.supplierId) ?? row.supplierId,
    },
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
            <>
              <Button
                variant="secondary"
                onClick={() => approve.mutate(row.id)}
                loading={approve.isPending}
              >
                Aprobar
              </Button>
              <Button variant="ghost" onClick={() => setSubmitInvoiceId(row.id)}>
                Enviar a aprobación
              </Button>
            </>
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
          disabled={expenseAccounts.length === 0 || payableAccounts.length === 0 || suppliers.length === 0}
        >
          Registrar factura de proveedor
        </Button>
        {expenseAccounts.length === 0 || payableAccounts.length === 0 ? (
          <p className="nx-field__error">
            Necesitas al menos una cuenta EXPENSE y una LIABILITY en el catálogo contable.
          </p>
        ) : null}
        {suppliers.length === 0 ? (
          <p className="nx-field__error">
            Necesitas al menos un proveedor registrado (Abastecimiento → Proveedores).
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
          suppliers={suppliers}
          onClose={() => setOpenCreate(false)}
          onCreated={() =>
            queryClient.invalidateQueries({
              queryKey: ['ap', 'supplier-invoices', activeCompanyId],
            })
          }
        />
      ) : null}

      {submitInvoiceId && activeCompanyId ? (
        <SubmitForApprovalModal
          invoiceId={submitInvoiceId}
          companyId={activeCompanyId}
          onClose={() => setSubmitInvoiceId(null)}
          onSubmitted={() =>
            queryClient.invalidateQueries({
              queryKey: ['ap', 'supplier-invoices', activeCompanyId],
            })
          }
        />
      ) : null}
    </div>
  )
}

/** Ver DEFERRED-FINAL-016 / docs/DEFERRED.md: `approval_service.create_request`
 * ahora tiene un llamador real -- este modal es ese punto de entrada.
 * DEFERRED-FINAL-015 (resuelto): el aprobador ahora se elige de un
 * directorio real de usuarios de la compañía (`GET /master-data/users`),
 * no un UUID en texto libre. INV-SOD-001 se sigue validando en el
 * backend (el propio solicitante nunca aparece como opción válida más
 * allá de lo que el backend rechace explícitamente). */
function SubmitForApprovalModal({
  invoiceId,
  companyId,
  onClose,
  onSubmitted,
}: {
  invoiceId: string
  companyId: string
  onClose: () => void
  onSubmitted: () => void
}) {
  const { users: companyUsers } = useCompanyUsers(companyId)
  const { user: currentUser } = useAuth()
  const [assignedTo, setAssignedTo] = useState('')
  const handleMutationError = useMutationError()

  const mutation = useMutation({
    mutationFn: () => apService.submitForApproval(invoiceId, assignedTo),
    onSuccess: () => {
      onSubmitted()
      onClose()
    },
    onError: (error) => handleMutationError(error, 'Enviar factura a aprobación'),
  })

  return (
    <Modal open title="Enviar factura a aprobación" onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <Select
          name="assignedTo"
          label="Usuario aprobador"
          value={assignedTo}
          onChange={(e) => setAssignedTo(e.target.value)}
          required
        >
          <option value="">Selecciona un aprobador…</option>
          {companyUsers
            .filter((u) => u.id !== currentUser?.id)
            .map((u) => (
              <option key={u.id} value={u.id}>
                {u.fullName} ({u.email})
              </option>
            ))}
        </Select>
        {mutation.isError ? (
          <p className="nx-field__error">{(mutation.error as Error).message}</p>
        ) : null}
        <Button type="submit" loading={mutation.isPending} disabled={!assignedTo}>
          Enviar
        </Button>
      </form>
    </Modal>
  )
}

function CreateSupplierInvoiceModal({
  companyId,
  expenseAccounts,
  payableAccounts,
  suppliers,
  onClose,
  onCreated,
}: {
  companyId: string
  expenseAccounts: { id: string; name: string }[]
  payableAccounts: { id: string; name: string }[]
  suppliers: { id: string; legalName: string }[]
  onClose: () => void
  onCreated: (invoice: SupplierInvoice) => void
}) {
  const [supplierId, setSupplierId] = useState<string | null>(null)
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [amount, setAmount] = useState<number | null>(null)
  const [expenseAccountId, setExpenseAccountId] = useState(expenseAccounts[0]?.id ?? '')
  const [payableAccountId, setPayableAccountId] = useState(payableAccounts[0]?.id ?? '')
  const handleMutationError = useMutationError()

  const supplierOptions = suppliers.map((s) => ({ id: s.id, label: s.legalName }))

  const mutation = useMutation({
    mutationFn: () =>
      apService.createInvoice({
        companyId,
        supplierId,
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
    onError: (error) => handleMutationError(error, 'Registrar factura de proveedor'),
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
        <SupplierSelector options={supplierOptions} value={supplierId} onChange={setSupplierId} />
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
          disabled={!amount || !supplierId || !invoiceNumber}
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
  const handleMutationError = useMutationError()
  const mutation = useMutation({
    mutationFn: async ({
      payload,
      idempotencyKey,
    }: {
      payload: Record<string, unknown>
      idempotencyKey: string
    }) => {
      await apService.pay(invoiceId, payload, idempotencyKey)
      return apService.getInvoice(invoiceId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-invoices'] })
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
    },
    onError: (error) => handleMutationError(error, 'Pagar factura de proveedor'),
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
            paymentDate: new Date().toISOString().slice(0, 10),
          },
          idempotencyKey: crypto.randomUUID(),
        })
      }
    >
      Pagar saldo ({remaining.toFixed(2)})
    </Button>
  )
}
