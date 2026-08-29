import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  Card,
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
import {
  arService,
  type CustomerInvoice,
  type CustomerReceipt,
} from '../../services/apArService'
import { crmService } from '../../services/crmService'
import { projectService } from '../../services/projectService'
import { treasuryService } from '../../services/treasuryService'
import { formatMoney } from '../../utils/currency'
import { statusLabel } from '../../utils/statusLabels'
import type { TreasuryAccount } from '../../types/treasury'
import '../treasury/TreasuryPage.css'

export function CollectionsPage() {
  const queryClient = useQueryClient()
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } = useActiveCompany()
  const [collectInvoice, setCollectInvoice] = useState<CustomerInvoice | null>(null)
  const [historyInvoice, setHistoryInvoice] = useState<CustomerInvoice | null>(null)

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
  const treasuryQuery = useQuery({
    queryKey: ['treasury', 'accounts', activeCompanyId],
    queryFn: () => treasuryService.listAccounts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  if (isLoading) return <LoadingState label="Cargando cobros…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return <EmptyState icon="bank" title="No hay compañía configurada" description="Configura la compañía antes de registrar cobros." />
  }

  const invoices = invoicesQuery.data ?? []
  const customers = customersQuery.data ?? []
  const projects = Array.isArray(projectsQuery.data) ? projectsQuery.data : []
  const treasuryAccounts = treasuryQuery.data ?? []
  const customerNames = new Map(customers.map((customer) => [customer.id, customer.legalName]))
  const projectNames = new Map(projects.map((project) => [project.id, `${project.code ? `${project.code} — ` : ''}${project.name}`]))
  const collectible = invoices.filter((invoice) => ['APPROVED', 'PARTIALLY_COLLECTED'].includes(invoice.status))
  const totalOutstanding = collectible.reduce((sum, invoice) => sum + Math.max(0, invoice.amount - invoice.amountCollected), 0)
  const collected = invoices.reduce((sum, invoice) => sum + invoice.amountCollected, 0)

  const columns: TableColumn<CustomerInvoice>[] = [
    { key: 'invoice', header: 'Factura', render: (row) => <strong>{row.invoiceNumber}</strong> },
    { key: 'customer', header: 'Cliente', render: (row) => customerNames.get(row.customerId) ?? 'Cliente no disponible' },
    {
      key: 'context',
      header: 'Contexto',
      render: (row) => row.projectId ? <Link to={`/proyectos/${row.projectId}`}>{projectNames.get(row.projectId) ?? 'Proyecto'}</Link> : statusLabel(row.scope),
    },
    { key: 'due', header: 'Vence', render: (row) => row.dueDate },
    { key: 'amount', header: 'Facturado', render: (row) => formatMoney(row.amount, row.currencyCode) },
    { key: 'collected', header: 'Cobrado', render: (row) => formatMoney(row.amountCollected, row.currencyCode) },
    { key: 'balance', header: 'Pendiente', render: (row) => formatMoney(Math.max(0, row.amount - row.amountCollected), row.currencyCode) },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{statusLabel(row.status)}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <div className="nx-treasury__actions">
          {['APPROVED', 'PARTIALLY_COLLECTED'].includes(row.status) ? (
            <Button onClick={() => setCollectInvoice(row)}>Registrar cobro</Button>
          ) : null}
          {row.amountCollected > 0 ? (
            <Button variant="secondary" onClick={() => setHistoryInvoice(row)}>Historial</Button>
          ) : null}
        </div>
      ),
    },
  ]

  return (
    <div className="nx-treasury">
      <header className="nx-treasury__header">
        <div>
          <p className="nx-page__eyebrow">Comercial</p>
          <h1 className="nx-dashboard__title">Cobros</h1>
          <p className="nx-field__hint">Aplica entradas reales de Tesorería a facturas emitidas. Los reversals preservan el recibo original.</p>
        </div>
        <Select value={activeCompanyId ?? ''} onChange={(event) => setActiveCompanyId(event.target.value)} aria-label="Compañía">
          {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
        </Select>
      </header>

      <div className="nx-dashboard__kpi-grid">
        <Card title="Pendiente de cobro"><strong>{formatMoney(totalOutstanding, 'HNL')}</strong></Card>
        <Card title="Cobrado acumulado"><strong>{formatMoney(collected, 'HNL')}</strong></Card>
        <Card title="Facturas pendientes"><strong>{collectible.length}</strong></Card>
      </div>

      {invoicesQuery.isLoading ? <LoadingState label="Cargando cartera…" /> : invoicesQuery.isError ? (
        <ErrorState description="No se pudo cargar la cartera de clientes." onRetry={() => invoicesQuery.refetch()} />
      ) : (
        <Table columns={columns} rows={invoices} getRowKey={(row) => row.id} emptyMessage="No hay facturas emitidas para gestionar cobros." />
      )}

      {collectInvoice ? (
        <CollectModal
          invoice={collectInvoice}
          treasuryAccounts={treasuryAccounts}
          onClose={() => setCollectInvoice(null)}
          onCollected={() => {
            queryClient.invalidateQueries({ queryKey: ['ar', 'customer-invoices', activeCompanyId] })
            queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts', activeCompanyId] })
          }}
        />
      ) : null}

      {historyInvoice ? (
        <ReceiptHistoryModal
          invoice={historyInvoice}
          treasuryAccounts={treasuryAccounts}
          onClose={() => setHistoryInvoice(null)}
          onReversed={() => {
            queryClient.invalidateQueries({ queryKey: ['ar', 'customer-invoices', activeCompanyId] })
            queryClient.invalidateQueries({ queryKey: ['ar', 'customer-receipts', historyInvoice.id] })
            queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts', activeCompanyId] })
          }}
        />
      ) : null}
    </div>
  )
}

function CollectModal({ invoice, treasuryAccounts, onClose, onCollected }: {
  invoice: CustomerInvoice
  treasuryAccounts: TreasuryAccount[]
  onClose: () => void
  onCollected: () => void
}) {
  const handleMutationError = useMutationError()
  const eligible = useMemo(
    () => treasuryAccounts.filter((account) => account.status === 'ACTIVE' && account.currencyCode === invoice.currencyCode),
    [invoice.currencyCode, treasuryAccounts],
  )
  const remaining = invoice.amount - invoice.amountCollected
  const [treasuryAccountId, setTreasuryAccountId] = useState(eligible[0]?.id ?? '')
  const [amount, setAmount] = useState<number | null>(remaining)
  const [receiptDate, setReceiptDate] = useState(new Date().toISOString().slice(0, 10))

  const collect = useMutation({
    mutationFn: () => arService.collect(
      invoice.id,
      { treasuryAccountId, amount: String(amount ?? 0), receiptDate },
      crypto.randomUUID(),
    ),
    onSuccess: () => { onCollected(); onClose() },
    onError: (error) => handleMutationError(error, 'Registrar cobro'),
  })

  return (
    <Modal open title={`Cobrar ${invoice.invoiceNumber}`} onClose={onClose}>
      <form className="nx-treasury__form" onSubmit={(event) => { event.preventDefault(); collect.mutate() }}>
        <p className="nx-field__hint">Saldo pendiente: {formatMoney(remaining, invoice.currencyCode)}</p>
        <Select label="Cuenta de Tesorería receptora" value={treasuryAccountId} onChange={(event) => setTreasuryAccountId(event.target.value)} required>
          <option value="">Selecciona la cuenta real…</option>
          {eligible.map((account) => <option key={account.id} value={account.id}>{account.name} — {account.currencyCode}</option>)}
        </Select>
        <MoneyInput label={`Monto (${invoice.currencyCode})`} value={amount} onChange={setAmount} />
        <Input label="Fecha del cobro" type="date" value={receiptDate} onChange={(event) => setReceiptDate(event.target.value)} required />
        {eligible.length === 0 ? <p className="nx-field__error">No hay una cuenta de Tesorería activa en {invoice.currencyCode}.</p> : null}
        <Button type="submit" loading={collect.isPending} disabled={!treasuryAccountId || !amount || amount <= 0 || amount > remaining || !receiptDate}>Aplicar cobro</Button>
      </form>
    </Modal>
  )
}

function ReceiptHistoryModal({ invoice, treasuryAccounts, onClose, onReversed }: {
  invoice: CustomerInvoice
  treasuryAccounts: TreasuryAccount[]
  onClose: () => void
  onReversed: () => void
}) {
  const handleMutationError = useMutationError()
  const [reverseReceipt, setReverseReceipt] = useState<CustomerReceipt | null>(null)
  const [reason, setReason] = useState('')
  const receiptsQuery = useQuery({
    queryKey: ['ar', 'customer-receipts', invoice.id],
    queryFn: () => arService.listReceipts(invoice.id),
  })
  const accountNames = new Map(treasuryAccounts.map((account) => [account.id, account.name]))
  const reverse = useMutation({
    mutationFn: () => arService.reverseReceipt(reverseReceipt as CustomerReceipt extends never ? never : string, reason),
  })

  const executeReverse = useMutation({
    mutationFn: ({ receiptId, reasonText }: { receiptId: string; reasonText: string }) => arService.reverseReceipt(receiptId, reasonText),
    onSuccess: () => {
      setReverseReceipt(null)
      setReason('')
      onReversed()
    },
    onError: (error) => handleMutationError(error, 'Revertir cobro'),
  })
  void reverse

  const columns: TableColumn<CustomerReceipt>[] = [
    { key: 'date', header: 'Fecha', render: (row) => row.receiptDate },
    { key: 'account', header: 'Cuenta receptora', render: (row) => accountNames.get(row.treasuryAccountId) ?? 'Cuenta de Tesorería' },
    { key: 'amount', header: 'Monto', render: (row) => formatMoney(Number(row.amount), invoice.currencyCode) },
    { key: 'document', header: 'Documento GL', render: (row) => <code>{row.accountingDocumentId.slice(0, 8)}…</code> },
    { key: 'actions', header: 'Acciones', render: (row) => <Button variant="secondary" onClick={() => setReverseReceipt(row)}>Revertir</Button> },
  ]

  return (
    <Modal open title={`Historial de cobros · ${invoice.invoiceNumber}`} onClose={onClose}>
      {receiptsQuery.isLoading ? <LoadingState label="Cargando historial…" /> : receiptsQuery.isError ? (
        <ErrorState description="No se pudo cargar el historial de cobros." onRetry={() => receiptsQuery.refetch()} />
      ) : (
        <Table columns={columns} rows={receiptsQuery.data ?? []} getRowKey={(row) => row.id} emptyMessage="No hay cobros registrados para esta factura." />
      )}
      {reverseReceipt ? (
        <div className="nx-treasury__form">
          <p><strong>Reversal formal</strong></p>
          <p className="nx-field__hint">Se conservará el cobro original y se creará un asiento inverso. No se elimina historial.</p>
          <Input label="Motivo" value={reason} onChange={(event) => setReason(event.target.value)} required />
          <div className="nx-treasury__actions">
            <Button variant="secondary" onClick={() => { setReverseReceipt(null); setReason('') }}>Cancelar</Button>
            <Button loading={executeReverse.isPending} disabled={reason.trim().length < 3} onClick={() => executeReverse.mutate({ receiptId: reverseReceipt.id, reasonText: reason.trim() })}>Confirmar reversal</Button>
          </div>
        </div>
      ) : null}
    </Modal>
  )
}
