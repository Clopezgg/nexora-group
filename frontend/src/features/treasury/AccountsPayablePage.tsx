import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  EmptyState,
  FilterBar,
  Input,
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
import { projectService } from '../../services/projectService'
import { procurementService } from '../../services/procurementService'
import {
  SUPPLIER_CONTRACT_CATEGORY_LABELS,
  type SupplierContract,
} from '../../types/procurement'
import { treasuryService } from '../../services/treasuryService'
import { apService, type SupplierInvoice } from '../../services/apArService'
import { formatMoney } from '../../utils/currency'
import type { TreasuryAccount } from '../../types/treasury'
import {
  ContractInstallmentPanel,
  type ContractAllocationDraft,
} from './ContractInstallmentPanel'
import './TreasuryPage.css'

export function AccountsPayablePage() {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const [companyId, setCompanyId] = useState<string | null>(null)
  const [openCreate, setOpenCreate] = useState(false)
  const [submitInvoiceId, setSubmitInvoiceId] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState('')
  const [filterSupplier, setFilterSupplier] = useState('')

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
  const contracts = contractsQuery.data ?? []
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
      render: (row) => formatMoney(row.amount, row.currencyCode),
    },
    { key: 'amountPaid', header: 'Pagado', render: (row) => formatMoney(row.amountPaid, row.currencyCode) },
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
              invoice={row}
              companyId={activeCompanyId as string}
              treasuryAccounts={treasuryAccounts}
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

      {invoices.length > 0 ? (
        <FilterBar
          onClear={() => {
            setFilterStatus('')
            setFilterSupplier('')
          }}
        >
          <Select
            label="Estado"
            value={filterStatus}
            onChange={(event) => setFilterStatus(event.target.value)}
          >
            <option value="">Todos</option>
            {['DRAFT', 'APPROVED', 'SCHEDULED', 'PARTIALLY_PAID', 'PAID', 'CANCELLED'].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </Select>
          <Select
            label="Proveedor"
            value={filterSupplier}
            onChange={(event) => setFilterSupplier(event.target.value)}
          >
            <option value="">Todos</option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.legalName}
              </option>
            ))}
          </Select>
        </FilterBar>
      ) : null}

      <Table
        columns={columns}
        rows={invoices.filter(
          (row) =>
            (!filterStatus || row.status === filterStatus) &&
            (!filterSupplier || row.supplierId === filterSupplier),
        )}
        getRowKey={(row) => row.id}
        emptyMessage="Aún no hay facturas de proveedor registradas."
      />

      {openCreate && activeCompanyId ? (
        <CreateSupplierInvoiceModal
          companyId={activeCompanyId}
          expenseAccounts={expenseAccounts}
          payableAccounts={payableAccounts}
          suppliers={suppliers}
          contracts={contracts}
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
  contracts,
  onClose,
  onCreated,
}: {
  companyId: string
  expenseAccounts: { id: string; name: string }[]
  payableAccounts: { id: string; name: string }[]
  suppliers: { id: string; legalName: string }[]
  contracts: SupplierContract[]
  onClose: () => void
  onCreated: (invoice: SupplierInvoice) => void
}) {
  const [supplierContractId, setSupplierContractId] = useState('')
  const [supplierId, setSupplierId] = useState<string | null>(null)
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [amount, setAmount] = useState<number | null>(null)
  const [scope, setScope] = useState<'CENTRAL' | 'GENERAL' | 'PROJECT'>('GENERAL')
  const [projectId, setProjectId] = useState('')
  const [expenseAccountId, setExpenseAccountId] = useState(expenseAccounts[0]?.id ?? '')
  const [payableAccountId, setPayableAccountId] = useState(payableAccounts[0]?.id ?? '')
  const handleMutationError = useMutationError()

  const selectedContract = contracts.find((c) => c.id === supplierContractId) ?? null

  // Al elegir un contrato de ejecución, la factura hereda su proveedor,
  // proyecto y moneda (ORDEN MAESTRA §14/§22): el contrato manda.
  function applyContract(nextContractId: string) {
    setSupplierContractId(nextContractId)
    const contract = contracts.find((c) => c.id === nextContractId)
    if (!contract) return
    setSupplierId(contract.supplierId)
    if (contract.projectId) {
      setScope('PROJECT')
      setProjectId(contract.projectId)
    }
  }

  const projectsQuery = useQuery({
    queryKey: ['projects', companyId],
    queryFn: () => projectService.list(companyId),
  })
  const projects = Array.isArray(projectsQuery.data) ? projectsQuery.data : []

  const supplierOptions = suppliers.map((s) => ({ id: s.id, label: s.legalName }))

  const mutation = useMutation({
    mutationFn: () =>
      apService.createInvoice({
        companyId,
        supplierId,
        supplierContractId: supplierContractId || null,
        invoiceNumber,
        scope,
        projectId: scope === 'PROJECT' ? projectId : null,
        expenseAccountId,
        payableAccountId,
        currencyCode: selectedContract?.currencyCode ?? 'HNL',
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
        <Select
          label="Contrato de ejecución (opcional)"
          value={supplierContractId}
          onChange={(event) => applyContract(event.target.value)}
        >
          <option value="">Sin contrato — factura suelta</option>
          {contracts.map((contract) => (
            <option key={contract.id} value={contract.id}>
              {contract.contractNumber} ·{' '}
              {SUPPLIER_CONTRACT_CATEGORY_LABELS[contract.contractCategory] ??
                contract.contractCategory}
            </option>
          ))}
        </Select>
        {selectedContract ? (
          <p className="nx-field__hint">
            La factura hereda el proveedor, el proyecto y la moneda del contrato. Al pagarla, el
            monto se asignará por FIFO a las cuotas del plan de pagos.
          </p>
        ) : null}
        <Select
          label="Alcance de la operación"
          value={scope}
          onChange={(event) => {
            const next = event.target.value as 'CENTRAL' | 'GENERAL' | 'PROJECT'
            setScope(next)
            if (next !== 'PROJECT') setProjectId('')
          }}
        >
          <option value="CENTRAL">Central — Tesorería corporativa</option>
          <option value="GENERAL">General — Sin proyecto</option>
          <option value="PROJECT">Proyecto — Operación atribuible</option>
        </Select>
        {scope === 'PROJECT' ? (
          <Select
            label="Proyecto"
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
            required
          >
            <option value="">Selecciona un proyecto…</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.code ? `${project.code} — ` : ''}{project.name}
              </option>
            ))}
          </Select>
        ) : null}
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
          disabled={!amount || !supplierId || !invoiceNumber || (scope === 'PROJECT' && !projectId)}
        >
          Registrar
        </Button>
      </form>
    </Modal>
  )
}

function PaySupplierInvoiceButton({
  invoice,
  companyId,
  treasuryAccounts,
  remaining,
}: {
  invoice: SupplierInvoice
  companyId: string
  treasuryAccounts: TreasuryAccount[]
  remaining: number
}) {
  const invoiceId = invoice.id
  const currencyCode = invoice.currencyCode
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const eligibleTreasuryAccounts = treasuryAccounts.filter(
    (account) => account.status === 'ACTIVE' && account.currencyCode === currencyCode,
  )
  const [open, setOpen] = useState(false)
  const [treasuryAccountId, setTreasuryAccountId] = useState(eligibleTreasuryAccounts[0]?.id ?? '')
  const [amount, setAmount] = useState<number | null>(remaining)
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().slice(0, 10))
  const [bankReference, setBankReference] = useState('')
  const [observations, setObservations] = useState('')
  const [contractAllocations, setContractAllocations] = useState<ContractAllocationDraft[]>([])
  const [allocationValid, setAllocationValid] = useState(true)
  const [contractHasSchedule, setContractHasSchedule] = useState(false)

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
      setOpen(false)
    },
    onError: (error) => handleMutationError(error, 'Pagar factura de proveedor'),
  })

  return (
    <>
      <Button
        variant="ghost"
        onClick={() => setOpen(true)}
        disabled={eligibleTreasuryAccounts.length === 0}
      >
        Pagar saldo ({formatMoney(remaining, currencyCode)})
      </Button>
      {open ? (
        <Modal open title="Pagar factura de proveedor" onClose={() => setOpen(false)}>
          <form
            className="nx-treasury__form"
            onSubmit={(event) => {
              event.preventDefault()
              mutation.mutate({
                payload: {
                  treasuryAccountId,
                  amount: String(amount ?? 0),
                  paymentDate,
                  bankTransactionReference: bankReference.trim() || undefined,
                  paymentObservations: observations.trim() || undefined,
                  contractAllocations:
                    contractHasSchedule && contractAllocations.length > 0
                      ? contractAllocations
                      : undefined,
                },
                idempotencyKey: crypto.randomUUID(),
              })
            }}
          >
            <Select
              name="paymentTreasuryAccountId"
              label="Cuenta pagadora"
              value={treasuryAccountId}
              onChange={(event) => setTreasuryAccountId(event.target.value)}
              required
            >
              {eligibleTreasuryAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name} — {account.currencyCode}
                </option>
              ))}
            </Select>
            <MoneyInput label={`Monto a pagar (${currencyCode})`} value={amount} onChange={setAmount} />
            <label className="nx-field">
              <span className="nx-field__label">Fecha de pago</span>
              <input
                className="nx-input"
                type="date"
                value={paymentDate}
                onChange={(event) => setPaymentDate(event.target.value)}
                required
              />
            </label>
            {invoice.supplierContractId ? (
              <ContractInstallmentPanel
                companyId={companyId}
                supplierContractId={invoice.supplierContractId}
                amount={amount}
                asOf={paymentDate}
                onChange={(rows, valid, hasSchedule) => {
                  setContractAllocations(rows)
                  setAllocationValid(valid)
                  setContractHasSchedule(hasSchedule)
                }}
              />
            ) : null}
            <Input
              label="Referencia bancaria del movimiento (opcional)"
              value={bankReference}
              onChange={(event) => setBankReference(event.target.value)}
              placeholder="p. ej. ATL-93829172"
            />
            <label className="nx-field">
              <span className="nx-field__label">Observaciones (opcional)</span>
              <textarea
                className="nx-textarea"
                value={observations}
                onChange={(event) => setObservations(event.target.value)}
                rows={2}
              />
            </label>
            <p className="nx-field__hint">
              El proyecto ya viene de la factura; aquí solo eliges desde qué banco o caja sale el dinero.
              La referencia bancaria y las observaciones quedan persistidas y se imprimen en el comprobante.
            </p>
            {mutation.isError ? (
              <p className="nx-field__error">{(mutation.error as Error).message}</p>
            ) : null}
            {contractHasSchedule && !allocationValid ? (
              <p className="nx-field__error" role="alert">
                No se puede confirmar el pago porque el monto no puede asignarse íntegramente al
                plan contractual. Revisa el plan o el monto.
              </p>
            ) : null}
            <Button
              type="submit"
              loading={mutation.isPending}
              disabled={
                !treasuryAccountId ||
                !amount ||
                amount <= 0 ||
                amount > remaining ||
                !paymentDate ||
                (contractHasSchedule && !allocationValid)
              }
            >
              Confirmar pago
            </Button>
          </form>
        </Modal>
      ) : null}
    </>
  )
}
