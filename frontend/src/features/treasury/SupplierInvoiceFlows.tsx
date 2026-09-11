import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
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
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { masterDataService } from '../../services/masterDataService'
import { projectService } from '../../services/projectService'
import { procurementService } from '../../services/procurementService'
import {
  SUPPLIER_CONTRACT_CATEGORY_LABELS,
  type SupplierContract,
} from '../../types/procurement'
import { treasuryService } from '../../services/treasuryService'
import { apService, type SupplierInvoice } from '../../services/apArService'
import { contractPaymentService } from '../../services/contractPaymentService'
import { apMetricsService } from '../../services/financialControlService'
import { formatMoney } from '../../utils/currency'
import { businessTodayIso } from '../../utils/businessDate'
import { statusLabel } from '../../utils/statusLabels'
import type { TreasuryAccount } from '../../types/treasury'
import {
  ContractInstallmentPanel,
  type ContractAllocationDraft,
} from './ContractInstallmentPanel'
import { PaymentEvidencePicker } from './PaymentEvidencePicker'
import './TreasuryPage.css'

const AP_FILTER_STATUSES = [
  'DRAFT',
  'REVIEW',
  'APPROVED',
  'SCHEDULED',
  'PARTIALLY_PAID',
  'PAID',
  'RECONCILED',
  'CANCELLED',
] as const

const PAYMENT_METHODS = [
  ['TRANSFER', 'Transferencia'],
  ['DEPOSIT', 'Depósito'],
  ['CHECK', 'Cheque'],
  ['CASH', 'Efectivo'],
  ['OTHER', 'Otro'],
] as const

type PaymentMethod = (typeof PAYMENT_METHODS)[number][0]

const METHODS_REQUIRING_EVIDENCE = new Set<PaymentMethod>(['TRANSFER', 'DEPOSIT', 'CHECK'])

/** Canonical AP obligation/payment flows shared by AP and Project Cockpit. */
export function AccountsPayablePage() {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const [openCreate, setOpenCreate] = useState(false)
  const [submitInvoiceId, setSubmitInvoiceId] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState('')
  const [filterSupplier, setFilterSupplier] = useState('')

  const { companies, activeCompanyId, setActiveCompanyId, isLoading: companiesLoading } = useActiveCompany()

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

  if (companiesLoading) return <LoadingState label="Cargando…" />
  if (companies.length === 0) {
    return (
      <EmptyState
        icon="card"
        title="Aún no hay compañías configuradas"
        description="Crea una compañía desde Tesorería antes de registrar facturas de proveedor."
      />
    )
  }

  const expenseAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'EXPENSE' || a.accountType === 'ASSET')
  const payableAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'LIABILITY')
  const treasuryAccounts = treasuryAccountsQuery.data ?? []
  const invoices = invoicesQuery.data ?? []
  const suppliers = suppliersQuery.data ?? []
  const contracts = contractsQuery.data ?? []
  const supplierNameById = new Map(suppliers.map((s) => [s.id, s.legalName]))

  const columns: TableColumn<SupplierInvoice>[] = [
    { key: 'invoiceNumber', header: 'Factura / obligación', render: (row) => row.invoiceNumber },
    {
      key: 'supplierId',
      header: 'Proveedor / contratista',
      render: (row) => supplierNameById.get(row.supplierId) ?? 'Tercero no disponible',
    },
    { key: 'amount', header: 'Monto', numeric: true, render: (row) => formatMoney(row.amount, row.currencyCode) },
    { key: 'amountPaid', header: 'Pagado', numeric: true, render: (row) => formatMoney(row.amountPaid, row.currencyCode) },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{statusLabel(row.status)}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <div className="nx-treasury__actions">
          {row.status === 'DRAFT' ? (
            <>
              <Button variant="secondary" onClick={() => approve.mutate(row.id)} loading={approve.isPending}>
                Aprobar
              </Button>
              <Button variant="ghost" onClick={() => setSubmitInvoiceId(row.id)}>
                Enviar a aprobación
              </Button>
            </>
          ) : null}
          {['APPROVED', 'SCHEDULED', 'PARTIALLY_PAID'].includes(row.status) && treasuryAccounts.length > 0 ? (
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
        <div>
          <h1 className="nx-dashboard__title">Cuentas por pagar</h1>
          <p className="nx-field__hint">Obligación → aprobación → pago → Tesorería/GL → evidencia → comprobante, sin duplicar el evento.</p>
        </div>
        <Select value={activeCompanyId ?? ''} onChange={(e) => setActiveCompanyId(e.target.value)} aria-label="Compañía">
          {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
        </Select>
      </header>

      <ApMetricsCard companyId={activeCompanyId} />

      <Card title="Acciones">
        <Button
          variant="secondary"
          onClick={() => setOpenCreate(true)}
          disabled={expenseAccounts.length === 0 || payableAccounts.length === 0 || suppliers.length === 0}
        >
          Registrar factura / obligación de proveedor
        </Button>
        {expenseAccounts.length === 0 || payableAccounts.length === 0 ? (
          <p className="nx-field__error">Necesitas una cuenta de contrapartida (gasto/activo) y una LIABILITY de cuentas por pagar.</p>
        ) : null}
        {suppliers.length === 0 ? <p className="nx-field__error">Necesitas al menos un proveedor o contratista registrado.</p> : null}
      </Card>

      {invoices.length > 0 ? (
        <FilterBar onClear={() => { setFilterStatus(''); setFilterSupplier('') }}>
          <Select label="Estado" value={filterStatus} onChange={(event) => setFilterStatus(event.target.value)}>
            <option value="">Todos</option>
            {AP_FILTER_STATUSES.map((s) => <option key={s} value={s}>{statusLabel(s)}</option>)}
          </Select>
          <Select label="Proveedor / contratista" value={filterSupplier} onChange={(event) => setFilterSupplier(event.target.value)}>
            <option value="">Todos</option>
            {suppliers.map((s) => <option key={s.id} value={s.id}>{s.legalName}</option>)}
          </Select>
        </FilterBar>
      ) : null}

      <Table
        columns={columns}
        rows={invoices.filter((row) => (!filterStatus || row.status === filterStatus) && (!filterSupplier || row.supplierId === filterSupplier))}
        getRowKey={(row) => row.id}
        emptyMessage="Aún no hay facturas u obligaciones de proveedor registradas."
      />

      {openCreate && activeCompanyId ? (
        <CreateSupplierInvoiceModal
          companyId={activeCompanyId}
          expenseAccounts={expenseAccounts}
          payableAccounts={payableAccounts}
          suppliers={suppliers}
          contracts={contracts}
          onClose={() => setOpenCreate(false)}
          onCreated={() => queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-invoices', activeCompanyId] })}
        />
      ) : null}

      {submitInvoiceId && activeCompanyId ? (
        <SubmitForApprovalModal
          invoiceId={submitInvoiceId}
          companyId={activeCompanyId}
          onClose={() => setSubmitInvoiceId(null)}
          onSubmitted={() => queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-invoices', activeCompanyId] })}
        />
      ) : null}
    </div>
  )
}

function SubmitForApprovalModal({ invoiceId, companyId, onClose, onSubmitted }: {
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
    onSuccess: () => { onSubmitted(); onClose() },
    onError: (error) => handleMutationError(error, 'Enviar factura a aprobación'),
  })
  return (
    <Modal open title="Enviar obligación a aprobación" onClose={onClose}>
      <form className="nx-treasury__form" onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
        <Select name="assignedTo" label="Usuario aprobador" value={assignedTo} onChange={(e) => setAssignedTo(e.target.value)} required>
          <option value="">Selecciona un aprobador…</option>
          {companyUsers.filter((u) => u.id !== currentUser?.id).map((u) => <option key={u.id} value={u.id}>{u.fullName} ({u.email})</option>)}
        </Select>
        {mutation.isError ? <p className="nx-field__error">{(mutation.error as Error).message}</p> : null}
        <Button type="submit" loading={mutation.isPending} disabled={!assignedTo}>Enviar</Button>
      </form>
    </Modal>
  )
}

export function CreateSupplierInvoiceModal({
  companyId,
  expenseAccounts,
  payableAccounts,
  suppliers,
  contracts,
  initialContractId,
  initialInstallment,
  lockedProjectId,
  onClose,
  onCreated,
}: {
  companyId: string
  expenseAccounts: { id: string; name: string }[]
  payableAccounts: { id: string; name: string }[]
  suppliers: { id: string; legalName: string }[]
  contracts: SupplierContract[]
  initialContractId?: string
  initialInstallment?: { installmentId: string; remaining: string; dueDate: string; periodLabel: string }
  lockedProjectId?: string
  onClose: () => void
  onCreated: (invoice: SupplierInvoice) => void
}) {
  const initialContract = contracts.find((c) => c.id === initialContractId) ?? null
  const [supplierContractId, setSupplierContractId] = useState(initialContract?.id ?? '')
  const [contractInstallmentId, setContractInstallmentId] = useState(
    initialInstallment?.installmentId ?? '',
  )
  const [supplierId, setSupplierId] = useState<string | null>(initialContract?.supplierId ?? null)
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [amount, setAmount] = useState<number | null>(
    initialInstallment ? Number(initialInstallment.remaining) : null,
  )
  const initialProjectId = lockedProjectId ?? initialContract?.projectId ?? ''
  const [scope, setScope] = useState<'CENTRAL' | 'GENERAL' | 'PROJECT'>(initialProjectId ? 'PROJECT' : 'GENERAL')
  const [projectId, setProjectId] = useState(initialProjectId)
  const [expenseAccountId, setExpenseAccountId] = useState(expenseAccounts[0]?.id ?? '')
  const [payableAccountId, setPayableAccountId] = useState(payableAccounts[0]?.id ?? '')
  const [invoiceDate, setInvoiceDate] = useState(businessTodayIso())
  const [dueDate, setDueDate] = useState(
    initialInstallment?.dueDate ?? initialContract?.advanceDueDate ?? businessTodayIso(),
  )
  const handleMutationError = useMutationError()
  const selectedContract = contracts.find((c) => c.id === supplierContractId) ?? null
  const scheduleQuery = useQuery({
    queryKey: ['contract-payments', 'by-contract', supplierContractId],
    queryFn: () => contractPaymentService.getByContract(supplierContractId),
    enabled: Boolean(supplierContractId),
    retry: false,
  })

  function applyContract(nextContractId: string) {
    setSupplierContractId(nextContractId)
    setContractInstallmentId('')
    const contract = contracts.find((c) => c.id === nextContractId)
    if (!contract) return
    setSupplierId(contract.supplierId)
    if (contract.projectId) {
      setScope('PROJECT')
      setProjectId(contract.projectId)
    }
  }

  const projectsQuery = useQuery({ queryKey: ['projects', companyId], queryFn: () => projectService.list(companyId) })
  const projects = Array.isArray(projectsQuery.data) ? projectsQuery.data : []
  const supplierOptions = suppliers.map((s) => ({ id: s.id, label: s.legalName }))

  const mutation = useMutation({
    mutationFn: () => apService.createInvoice({
      companyId,
      supplierId,
      supplierContractId: supplierContractId || null,
      contractInstallmentId: contractInstallmentId || null,
      invoiceNumber,
      scope,
      projectId: scope === 'PROJECT' ? projectId : null,
      expenseAccountId,
      payableAccountId,
      currencyCode: selectedContract?.currencyCode ?? projects.find((p) => p.id === projectId)?.currencyCode ?? 'HNL',
      amount: String(amount ?? 0),
      invoiceDate,
      dueDate,
    }) as Promise<SupplierInvoice>,
    onSuccess: (invoice) => { onCreated(invoice); onClose() },
    onError: (error) => handleMutationError(error, 'Registrar factura de proveedor'),
  })

  return (
    <Modal open title="Registrar obligación de pago" onClose={onClose}>
      <form className="nx-treasury__form" onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
        <Select label="Contrato de ejecución (opcional)" value={supplierContractId} onChange={(event) => applyContract(event.target.value)} disabled={Boolean(initialContractId)}>
          <option value="">Sin contrato — factura suelta</option>
          {contracts.map((contract) => <option key={contract.id} value={contract.id}>{contract.contractNumber} · {SUPPLIER_CONTRACT_CATEGORY_LABELS[contract.contractCategory] ?? contract.contractCategory}</option>)}
        </Select>
        {selectedContract ? <p className="nx-field__hint">La obligación hereda tercero, proyecto y moneda del contrato. El pago se asignará al plan contractual.</p> : null}
        {initialInstallment ? (
          <p className="nx-field__hint">
            Cuota vinculada: {initialInstallment.periodLabel}. La factura representa exactamente su neto pendiente.
          </p>
        ) : null}
        {selectedContract && scheduleQuery.data && !initialInstallment ? (
          <Select
            label="Cuota contractual"
            value={contractInstallmentId}
            onChange={(event) => {
              const nextId = event.target.value
              const installment = scheduleQuery.data?.installments.find(
                (row) => row.installmentId === nextId,
              )
              setContractInstallmentId(nextId)
              if (installment) {
                setAmount(Number(installment.remaining))
                setDueDate(installment.dueDate)
              }
            }}
            required
          >
            <option value="">Selecciona la cuota exacta…</option>
            {scheduleQuery.data.installments
              .filter((row) => row.remaining !== '0.00' && row.status !== 'CANCELLED')
              .map((row) => (
                <option key={row.installmentId} value={row.installmentId}>
                  {row.periodLabel} — {formatMoney(row.remaining, selectedContract.currencyCode)}
                </option>
              ))}
          </Select>
        ) : null}
        <Select label="Alcance de la operación" value={scope} disabled={Boolean(lockedProjectId || selectedContract?.projectId)} onChange={(event) => {
          const next = event.target.value as 'CENTRAL' | 'GENERAL' | 'PROJECT'
          setScope(next)
          if (next !== 'PROJECT') setProjectId('')
        }}>
          <option value="CENTRAL">Central — Tesorería corporativa</option>
          <option value="GENERAL">General — Sin proyecto</option>
          <option value="PROJECT">Proyecto — Operación atribuible</option>
        </Select>
        {scope === 'PROJECT' ? (
          <Select label="Proyecto" value={projectId} disabled={Boolean(lockedProjectId || selectedContract?.projectId)} onChange={(event) => setProjectId(event.target.value)} required>
            <option value="">Selecciona un proyecto…</option>
            {projects.map((project) => <option key={project.id} value={project.id}>{project.code ? `${project.code} — ` : ''}{project.name}</option>)}
          </Select>
        ) : null}
        <SupplierSelector options={supplierOptions} value={supplierId} onChange={setSupplierId} />
        <Input label="Número de factura / obligación" value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} required />
        <Select label="Cuenta de contrapartida (gasto o activo/prepago)" value={expenseAccountId} onChange={(e) => setExpenseAccountId(e.target.value)}>
          {expenseAccounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </Select>
        <Select label="Cuenta por pagar" value={payableAccountId} onChange={(e) => setPayableAccountId(e.target.value)}>
          {payableAccounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </Select>
        <MoneyInput label="Monto" value={amount} onChange={setAmount} disabled={Boolean(initialInstallment)} />
        <Input label="Fecha económica de la obligación" type="date" value={invoiceDate} onChange={(e) => setInvoiceDate(e.target.value)} required />
        <Input label="Vencimiento contractual / comercial" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required disabled={Boolean(initialInstallment)} />
        {mutation.isError ? <p className="nx-field__error">{(mutation.error as Error).message}</p> : null}
        <Button type="submit" loading={mutation.isPending} disabled={!amount || !supplierId || !invoiceNumber || !invoiceDate || !dueDate || (scope === 'PROJECT' && !projectId) || Boolean(scheduleQuery.data && !contractInstallmentId)}>Registrar obligación</Button>
      </form>
    </Modal>
  )
}

export function PaySupplierInvoiceButton({
  invoice,
  companyId,
  treasuryAccounts,
  remaining,
  selectedInstallmentId,
  label,
  lockAmount = false,
}: {
  invoice: SupplierInvoice
  companyId: string
  treasuryAccounts: TreasuryAccount[]
  remaining: number
  selectedInstallmentId?: string | null
  label?: string
  lockAmount?: boolean
}) {
  const invoiceId = invoice.id
  const currencyCode = invoice.currencyCode
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const eligibleTreasuryAccounts = treasuryAccounts.filter((account) => account.status === 'ACTIVE' && account.currencyCode === currencyCode)
  const [open, setOpen] = useState(false)
  const [treasuryAccountId, setTreasuryAccountId] = useState(eligibleTreasuryAccounts[0]?.id ?? '')
  const [amount, setAmount] = useState<number | null>(remaining)
  const [paymentDate, setPaymentDate] = useState(businessTodayIso())
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('TRANSFER')
  const [paymentEvidenceIds, setPaymentEvidenceIds] = useState<string[]>([])
  const [evidenceUploading, setEvidenceUploading] = useState(false)
  const [bankReference, setBankReference] = useState('')
  const [observations, setObservations] = useState('')
  const [contractAllocations, setContractAllocations] = useState<ContractAllocationDraft[]>([])
  const [allocationValid, setAllocationValid] = useState(true)
  const [contractHasSchedule, setContractHasSchedule] = useState(false)
  const evidenceRequired = METHODS_REQUIRING_EVIDENCE.has(paymentMethod)

  const mutation = useMutation({
    mutationFn: async ({ payload, idempotencyKey }: { payload: Record<string, unknown>; idempotencyKey: string }) => {
      await apService.pay(invoiceId, payload, idempotencyKey)
      return apService.getInvoice(invoiceId)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-invoices'] })
      queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
      queryClient.invalidateQueries({ queryKey: ['contract-payments'] })
      queryClient.invalidateQueries({ queryKey: ['project'] })
      setOpen(false)
    },
    onError: (error) => handleMutationError(error, 'Pagar factura de proveedor'),
  })

  return (
    <>
      <Button variant="ghost" onClick={() => setOpen(true)} disabled={eligibleTreasuryAccounts.length === 0}>
        {label ?? `Pagar saldo (${formatMoney(remaining, currencyCode)})`}
      </Button>
      {open ? (
        <Modal open title="Registrar pago" onClose={() => setOpen(false)}>
          <form className="nx-treasury__form" onSubmit={(event) => {
            event.preventDefault()
            mutation.mutate({
              payload: {
                treasuryAccountId,
                amount: String(amount ?? 0),
                paymentDate,
                paymentMethod,
                paymentEvidenceIds,
                bankTransactionReference: bankReference.trim() || undefined,
                paymentObservations: observations.trim() || undefined,
                contractAllocations: contractHasSchedule && contractAllocations.length > 0 ? contractAllocations : undefined,
              },
              idempotencyKey: crypto.randomUUID(),
            })
          }}>
            <Select name="paymentTreasuryAccountId" label="Cuenta pagadora" value={treasuryAccountId} onChange={(event) => setTreasuryAccountId(event.target.value)} required>
              {eligibleTreasuryAccounts.map((account) => <option key={account.id} value={account.id}>{account.name} — {account.currencyCode}</option>)}
            </Select>
            <MoneyInput label={`Monto a pagar (${currencyCode})`} value={amount} onChange={setAmount} disabled={lockAmount} />
            <Input label="Fecha efectiva del pago (movimiento bancario)" type="date" value={paymentDate} onChange={(event) => setPaymentDate(event.target.value)} required />
            {invoice.supplierContractId ? (
              <>
                <ContractInstallmentPanel
                  companyId={companyId}
                  supplierContractId={invoice.supplierContractId}
                  amount={amount}
                  asOf={businessTodayIso()}
                  selectedInstallmentId={selectedInstallmentId}
                  onChange={(rows, valid, hasSchedule) => {
                    setContractAllocations(rows)
                    setAllocationValid(valid)
                    setContractHasSchedule(hasSchedule)
                  }}
                />
              </>
            ) : null}
            <Select label="Método de pago" value={paymentMethod} onChange={(event) => {
              const next = event.target.value as PaymentMethod
              setPaymentMethod(next)
              if (!METHODS_REQUIRING_EVIDENCE.has(next)) setPaymentEvidenceIds([])
            }}>
              {PAYMENT_METHODS.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
            </Select>
            <PaymentEvidencePicker
              key={`${invoiceId}-${paymentMethod}`}
              companyId={companyId}
              invoiceId={invoiceId}
              required={evidenceRequired}
              disabled={mutation.isPending}
              onChange={(ids, uploading) => { setPaymentEvidenceIds(ids); setEvidenceUploading(uploading) }}
            />
            <Input label="Referencia bancaria del movimiento (opcional)" value={bankReference} onChange={(event) => setBankReference(event.target.value)} placeholder="p. ej. ATL-93829172" />
            <label className="nx-field">
              <span className="nx-field__label">Observaciones (opcional)</span>
              <textarea className="nx-textarea" value={observations} onChange={(event) => setObservations(event.target.value)} rows={2} />
            </label>
            <p className="nx-field__hint">Al confirmar, el mismo evento actualiza AP, Tesorería, GL, plan contractual y trazabilidad. Transferencia, depósito y cheque no se contabilizan sin evidencia.</p>
            {mutation.isError ? <p className="nx-field__error">{(mutation.error as Error).message}</p> : null}
            {contractHasSchedule && !allocationValid ? <p className="nx-field__error" role="alert">El monto no puede asignarse íntegramente al plan contractual.</p> : null}
            <Button
              type="submit"
              loading={mutation.isPending}
              disabled={
                !treasuryAccountId || !amount || amount <= 0 || amount > remaining || !paymentDate ||
                (contractHasSchedule && !allocationValid) || evidenceUploading ||
                (evidenceRequired && paymentEvidenceIds.length === 0)
              }
            >
              Confirmar y contabilizar pago
            </Button>
          </form>
        </Modal>
      ) : null}
    </>
  )
}

function ApMetricsCard({ companyId }: { companyId: string | null }) {
  const query = useQuery({ queryKey: ['ap-metrics', companyId], queryFn: () => apMetricsService.get(companyId as string), enabled: Boolean(companyId) })
  if (!companyId) return null
  const m = query.data
  return (
    <Card title="Aging de cuentas por pagar">
      {query.isLoading ? <LoadingState label="Calculando aging…" /> : m?.aging ? (
        <div className="nx-treasury__actions" style={{ flexWrap: 'wrap' }}>
          <Badge>Cartera abierta {formatMoney(Number(m.apOutstanding ?? 0))}</Badge>
          <Badge tone="neutral">Al día {formatMoney(Number(m.aging.current ?? 0))}</Badge>
          <Badge tone="warning">1–30 {formatMoney(Number(m.aging['1_30'] ?? 0))}</Badge>
          <Badge tone="warning">31–60 {formatMoney(Number(m.aging['31_60'] ?? 0))}</Badge>
          <Badge tone="danger">61–90 {formatMoney(Number(m.aging['61_90'] ?? 0))}</Badge>
          <Badge tone="danger">+90 {formatMoney(Number(m.aging.over_90 ?? 0))}</Badge>
        </div>
      ) : null}
    </Card>
  )
}
