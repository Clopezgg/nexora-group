import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  Card,
  CustomerSelector,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Modal,
  MoneyInput,
  Select,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { arService, type CustomerInvoice } from '../../services/apArService'
import { crmService } from '../../services/crmService'
import { masterDataService } from '../../services/masterDataService'
import { projectService } from '../../services/projectService'
import { formatMoney } from '../../utils/currency'
import { statusLabel } from '../../utils/statusLabels'
import '../treasury/TreasuryPage.css'

export function BillingPage() {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } = useActiveCompany()
  const [createOpen, setCreateOpen] = useState(false)

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
  const projectsQuery = useQuery({
    queryKey: ['projects', activeCompanyId],
    queryFn: () => projectService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const accountsQuery = useQuery({
    queryKey: ['master-data', 'accounts', activeCompanyId],
    queryFn: () => masterDataService.listAccounts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const approve = useMutation({
    mutationFn: arService.approveInvoice,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ar', 'customer-invoices', activeCompanyId] }),
    onError: (error) => handleMutationError(error, 'Aprobar factura de cliente'),
  })

  if (isLoading) return <LoadingState label="Cargando facturación…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return <EmptyState icon="receipt" title="No hay compañía configurada" description="Configura la compañía antes de facturar." />
  }

  const invoices = invoicesQuery.data ?? []
  const customers = customersQuery.data ?? []
  const projects = Array.isArray(projectsQuery.data) ? projectsQuery.data : []
  const accounts = accountsQuery.data ?? []
  const customerNames = new Map(customers.map((customer) => [customer.id, customer.legalName]))
  const projectNames = new Map(projects.map((project) => [project.id, `${project.code ? `${project.code} — ` : ''}${project.name}`]))
  const totalBilled = invoices.reduce((sum, invoice) => sum + invoice.amount, 0)
  const outstanding = invoices.reduce((sum, invoice) => sum + Math.max(0, invoice.amount - invoice.amountCollected), 0)

  const columns: TableColumn<CustomerInvoice>[] = [
    { key: 'invoice', header: 'Factura', render: (row) => <strong>{row.invoiceNumber}</strong> },
    { key: 'customer', header: 'Cliente', render: (row) => customerNames.get(row.customerId) ?? 'Cliente no disponible' },
    {
      key: 'context',
      header: 'Contexto',
      render: (row) => row.projectId ? <Link to={`/proyectos/${row.projectId}`}>{projectNames.get(row.projectId) ?? 'Proyecto'}</Link> : statusLabel(row.scope),
    },
    { key: 'amount', header: 'Monto', render: (row) => formatMoney(row.amount, row.currencyCode) },
    { key: 'balance', header: 'Saldo', render: (row) => formatMoney(Math.max(0, row.amount - row.amountCollected), row.currencyCode) },
    { key: 'due', header: 'Vence', render: (row) => row.dueDate },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{statusLabel(row.status)}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => row.status === 'DRAFT' ? (
        <Button variant="secondary" loading={approve.isPending} onClick={() => approve.mutate(row.id)}>Aprobar</Button>
      ) : <span className="nx-field__hint">Documento emitido</span>,
    },
  ]

  return (
    <div className="nx-treasury">
      <header className="nx-treasury__header">
        <div>
          <p className="nx-page__eyebrow">Comercial</p>
          <h1 className="nx-dashboard__title">Facturación</h1>
          <p className="nx-field__hint">Documentos de cuentas por cobrar. Los cobros se registran en la pantalla Cobros.</p>
        </div>
        <Select value={activeCompanyId ?? ''} onChange={(event) => setActiveCompanyId(event.target.value)} aria-label="Compañía">
          {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
        </Select>
      </header>

      <div className="nx-dashboard__kpi-grid">
        <Card title="Facturado"><strong>{formatMoney(totalBilled, 'HNL')}</strong></Card>
        <Card title="Saldo por cobrar"><strong>{formatMoney(outstanding, 'HNL')}</strong></Card>
        <Card title="Documentos"><strong>{invoices.length}</strong></Card>
      </div>

      <Card title="Emisión de documentos">
        <Button onClick={() => setCreateOpen(true)}>Nueva factura</Button>
      </Card>

      {invoicesQuery.isLoading ? <LoadingState label="Cargando facturas…" /> : invoicesQuery.isError ? (
        <ErrorState description="No se pudieron cargar las facturas." onRetry={() => invoicesQuery.refetch()} />
      ) : (
        <Table columns={columns} rows={invoices} getRowKey={(row) => row.id} emptyMessage="Todavía no hay facturas de cliente. Usa Nueva factura para registrar la primera." />
      )}

      {createOpen && activeCompanyId ? (
        <BillingCreateModal
          companyId={activeCompanyId}
          customers={customers}
          projects={projects}
          revenueAccounts={accounts.filter((account) => account.accountType === 'REVENUE' && account.isPostable)}
          receivableAccounts={accounts.filter((account) => account.accountType === 'ASSET' && account.isPostable)}
          onClose={() => setCreateOpen(false)}
          onCreated={() => queryClient.invalidateQueries({ queryKey: ['ar', 'customer-invoices', activeCompanyId] })}
        />
      ) : null}
    </div>
  )
}

function BillingCreateModal({ companyId, customers, projects, revenueAccounts, receivableAccounts, onClose, onCreated }: {
  companyId: string
  customers: { id: string; legalName: string }[]
  projects: { id: string; name: string; code?: string | null }[]
  revenueAccounts: { id: string; name: string }[]
  receivableAccounts: { id: string; name: string }[]
  onClose: () => void
  onCreated: () => void
}) {
  const handleMutationError = useMutationError()
  const [customerId, setCustomerId] = useState<string | null>(null)
  const [invoiceNumber, setInvoiceNumber] = useState('')
  const [scope, setScope] = useState<'CENTRAL' | 'GENERAL' | 'PROJECT'>('GENERAL')
  const [projectId, setProjectId] = useState('')
  const [amount, setAmount] = useState<number | null>(null)
  const [invoiceDate, setInvoiceDate] = useState(new Date().toISOString().slice(0, 10))
  const [dueDate, setDueDate] = useState(new Date().toISOString().slice(0, 10))
  const [revenueAccountId, setRevenueAccountId] = useState(revenueAccounts[0]?.id ?? '')
  const [receivableAccountId, setReceivableAccountId] = useState(receivableAccounts[0]?.id ?? '')

  const create = useMutation({
    mutationFn: () => arService.createInvoice({
      companyId,
      customerId,
      invoiceNumber: invoiceNumber.trim(),
      scope,
      projectId: scope === 'PROJECT' ? projectId : null,
      revenueAccountId,
      receivableAccountId,
      currencyCode: 'HNL',
      amount: String(amount ?? 0),
      invoiceDate,
      dueDate,
    }),
    onSuccess: () => { onCreated(); onClose() },
    onError: (error) => handleMutationError(error, 'Crear factura'),
  })

  const configurationReady = customers.length > 0 && revenueAccounts.length > 0 && receivableAccounts.length > 0
  return (
    <Modal open title="Nueva factura de cliente" onClose={onClose}>
      {!configurationReady ? <p className="nx-field__error">Faltan clientes o cuentas contables postables REVENUE/ASSET. Configura los maestros antes de emitir.</p> : null}
      <form className="nx-treasury__form" onSubmit={(event) => { event.preventDefault(); create.mutate() }}>
        <CustomerSelector options={customers.map((customer) => ({ id: customer.id, label: customer.legalName }))} value={customerId} onChange={setCustomerId} />
        <Input label="Número de factura" value={invoiceNumber} onChange={(event) => setInvoiceNumber(event.target.value)} required />
        <Select label="Alcance" value={scope} onChange={(event) => { const next = event.target.value as typeof scope; setScope(next); if (next !== 'PROJECT') setProjectId('') }}>
          <option value="CENTRAL">Central</option><option value="GENERAL">General</option><option value="PROJECT">Proyecto</option>
        </Select>
        {scope === 'PROJECT' ? <Select label="Proyecto" value={projectId} onChange={(event) => setProjectId(event.target.value)} required><option value="">Selecciona…</option>{projects.map((project) => <option key={project.id} value={project.id}>{project.code ? `${project.code} — ` : ''}{project.name}</option>)}</Select> : null}
        <Select label="Cuenta de ingresos" value={revenueAccountId} onChange={(event) => setRevenueAccountId(event.target.value)}>{revenueAccounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</Select>
        <Select label="Cuenta por cobrar" value={receivableAccountId} onChange={(event) => setReceivableAccountId(event.target.value)}>{receivableAccounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</Select>
        <MoneyInput label="Monto HNL" value={amount} onChange={setAmount} />
        <Input label="Fecha de factura" type="date" value={invoiceDate} onChange={(event) => setInvoiceDate(event.target.value)} required />
        <Input label="Vencimiento" type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} required />
        {dueDate < invoiceDate ? <p className="nx-field__error">El vencimiento no puede ser anterior a la fecha de factura.</p> : null}
        <Button type="submit" loading={create.isPending} disabled={!configurationReady || !customerId || !invoiceNumber.trim() || !amount || amount <= 0 || !invoiceDate || !dueDate || dueDate < invoiceDate || (scope === 'PROJECT' && !projectId)}>Crear factura</Button>
      </form>
    </Modal>
  )
}
