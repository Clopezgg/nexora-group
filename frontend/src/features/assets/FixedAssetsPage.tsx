import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Modal,
  Select,
  MoneyInput,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { assetService } from '../../services/assetService'
import { apService } from '../../services/apArService'
import { masterDataService } from '../../services/masterDataService'
import { projectService } from '../../services/projectService'
import type { FixedAsset } from '../../types/asset'
import { businessTodayIso } from '../../utils/businessDate'

const STATUS_TONE: Record<FixedAsset['status'], 'success' | 'warning' | 'neutral' | 'danger'> = {
  ACTIVE: 'success',
  UNDER_MAINTENANCE: 'warning',
  DISPOSED: 'danger',
  RETIRED: 'neutral',
}

export function FixedAssetsPage() {
  const { activeCompanyId, activeCompany, isLoading: loadingCompanies } = useActiveCompany()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [depreciationAsset, setDepreciationAsset] = useState<FixedAsset | null>(null)
  const [disposalAsset, setDisposalAsset] = useState<FixedAsset | null>(null)

  const [form, setForm] = useState({
    supplierInvoiceId: '',
    category: '',
    name: '',
    acquisitionDate: '',
    cost: '',
    usefulLifeMonths: '12',
    salvageValue: '0',
    depreciationExpenseAccountId: '',
    accumulatedDepreciationAccountId: '',
    assetAccountId: '',
    acquisitionOffsetAccountId: '',
    scope: 'GENERAL' as 'GENERAL' | 'PROJECT',
    projectId: '',
  })

  const assetsQuery = useQuery({
    queryKey: ['assets', 'fixed-assets', activeCompanyId],
    queryFn: () => assetService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const accountsQuery = useQuery({
    queryKey: ['master-data', 'accounts', activeCompanyId],
    queryFn: () => masterDataService.listAccounts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const invoicesQuery = useQuery({
    queryKey: ['ap', 'supplier-invoices', activeCompanyId],
    queryFn: () => apService.listInvoices(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const projectsQuery = useQuery({
    queryKey: ['projects', activeCompanyId],
    queryFn: () => projectService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const depreciationQuery = useQuery({
    queryKey: ['assets', 'depreciation-entries', depreciationAsset?.id],
    queryFn: () => assetService.listDepreciationEntries(depreciationAsset!.id),
    enabled: Boolean(depreciationAsset),
  })

  const createMutation = useMutation({
    mutationFn: () => {
      if (form.supplierInvoiceId) {
        return assetService.createFromSupplierInvoice(form.supplierInvoiceId, {
          category: form.category,
          name: form.name,
          usefulLifeMonths: Number(form.usefulLifeMonths),
          salvageValue: form.salvageValue,
          assetAccountId: form.assetAccountId,
          depreciationExpenseAccountId: form.depreciationExpenseAccountId,
          accumulatedDepreciationAccountId: form.accumulatedDepreciationAccountId,
        })
      }
      return assetService.create({
        companyId: activeCompanyId as string,
        category: form.category,
        name: form.name,
        acquisitionDate: form.acquisitionDate,
        cost: form.cost,
        currencyCode: activeCompany?.functionalCurrencyCode ?? 'HNL',
        usefulLifeMonths: Number(form.usefulLifeMonths),
        salvageValue: form.salvageValue,
        scope: form.scope,
        projectId: form.scope === 'PROJECT' ? form.projectId || undefined : undefined,
        depreciationExpenseAccountId: form.depreciationExpenseAccountId,
        accumulatedDepreciationAccountId: form.accumulatedDepreciationAccountId,
        assetAccountId: form.assetAccountId,
        acquisitionOffsetAccountId: form.acquisitionOffsetAccountId,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets', 'fixed-assets', activeCompanyId] })
      setModalOpen(false)
      setForm({
        supplierInvoiceId: '',
        category: '',
        name: '',
        acquisitionDate: '',
        cost: '',
        usefulLifeMonths: '12',
        salvageValue: '0',
        depreciationExpenseAccountId: '',
        accumulatedDepreciationAccountId: '',
        assetAccountId: '',
        acquisitionOffsetAccountId: '',
        scope: 'GENERAL',
        projectId: '',
      })
    },
  })

  const generateDepreciationMutation = useMutation({
    mutationFn: (payload: { periodStart: string; periodEnd: string }) =>
      assetService.generateDepreciationEntry(depreciationAsset!.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets', 'depreciation-entries', depreciationAsset?.id] })
    },
  })

  const disposalMutation = useMutation({
    mutationFn: ({ assetId, disposalDate, proceeds, proceedsAccountId }: {
      assetId: string
      disposalDate: string
      proceeds: string
      proceedsAccountId?: string
    }) => assetService.dispose(assetId, { disposalDate, proceeds, proceedsAccountId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assets', 'fixed-assets', activeCompanyId] })
      setDisposalAsset(null)
    },
  })

  const columns: TableColumn<FixedAsset>[] = [
    { key: 'name', header: 'Activo', render: (row) => row.name },
    { key: 'category', header: 'Categoría', render: (row) => row.category },
    { key: 'cost', header: 'Costo', render: (row) => `${row.currencyCode} ${row.cost}` },
    {
      key: 'source',
      header: 'Origen',
      render: (row) => (row.supplierInvoiceId ? 'Factura proveedor' : 'Alta manual'),
    },
    { key: 'usefulLifeMonths', header: 'Vida útil (meses)', render: (row) => row.usefulLifeMonths },
    { key: 'status', header: 'Estado', render: (row) => <Badge tone={STATUS_TONE[row.status]}>{row.status}</Badge> },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="secondary" onClick={() => setDepreciationAsset(row)}>
            Depreciación
          </Button>
          {row.status !== 'DISPOSED' && row.status !== 'RETIRED' ? (
            <Button
              variant="ghost"
              onClick={() => setDisposalAsset(row)}
            >
              Dar de baja
            </Button>
          ) : null}
        </div>
      ),
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="tag"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

  const expenseAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'EXPENSE')
  const assetAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'ASSET')
  const capitalizableInvoices = (invoicesQuery.data ?? []).filter(
    (invoice) =>
      ['APPROVED', 'SCHEDULED', 'PARTIALLY_PAID', 'PAID', 'RECONCILED'].includes(
        invoice.status,
      ) && !(assetsQuery.data ?? []).some((asset) => asset.supplierInvoiceId === invoice.id),
  )

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Activos fijos</h1>
        <Button onClick={() => setModalOpen(true)}>Nuevo activo</Button>
      </header>

      <Card>
        {assetsQuery.isLoading ? (
          <LoadingState label="Cargando activos…" />
        ) : assetsQuery.isError ? (
          <ErrorState onRetry={() => assetsQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={assetsQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay activos fijos registrados."
          />
        )}
      </Card>

      <Modal open={modalOpen} title="Nuevo activo fijo" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Select
            label="Factura proveedor de origen · opcional"
            value={form.supplierInvoiceId}
            onChange={(e) => setForm({ ...form, supplierInvoiceId: e.target.value })}
          >
            <option value="">Alta manual</option>
            {capitalizableInvoices.map((invoice) => (
              <option key={invoice.id} value={invoice.id}>
                {invoice.invoiceNumber} · {invoice.currencyCode} {invoice.amount + invoice.taxAmount}
              </option>
            ))}
          </Select>
          <Input label="Categoría" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} required />
          <Input label="Nombre" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          {!form.supplierInvoiceId ? (
            <>
              <Input
                label="Fecha de adquisición"
                type="date"
                value={form.acquisitionDate}
                onChange={(e) => setForm({ ...form, acquisitionDate: e.target.value })}
                required
              />
              <Input label="Costo" value={form.cost} onChange={(e) => setForm({ ...form, cost: e.target.value })} required />
            </>
          ) : (
            <p className="nx-field__hint">
              Fecha, costo, moneda, ámbito y proyecto se heredarán de la factura aprobada; el sistema
              generará el asiento CAP automáticamente.
            </p>
          )}
          <Input
            label="Vida útil (meses)"
            type="number"
            value={form.usefulLifeMonths}
            onChange={(e) => setForm({ ...form, usefulLifeMonths: e.target.value })}
            required
          />
          <Input
            label="Valor de rescate"
            value={form.salvageValue}
            onChange={(e) => setForm({ ...form, salvageValue: e.target.value })}
          />
          {!form.supplierInvoiceId ? (
            <>
              <Select
                label="Ámbito"
                value={form.scope}
                onChange={(e) => setForm({ ...form, scope: e.target.value as 'GENERAL' | 'PROJECT', projectId: '' })}
              >
                <option value="GENERAL">General</option>
                <option value="PROJECT">Proyecto</option>
              </Select>
              {form.scope === 'PROJECT' ? (
                <Select
                  label="Proyecto"
                  value={form.projectId}
                  onChange={(e) => setForm({ ...form, projectId: e.target.value })}
                  required
                >
                  <option value="">Selecciona un proyecto</option>
                  {(projectsQuery.data ?? []).map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </Select>
              ) : null}
            </>
          ) : null}
          {form.supplierInvoiceId ? (
            <Select
              label="Cuenta de activo a capitalizar"
              value={form.assetAccountId}
              onChange={(e) => setForm({ ...form, assetAccountId: e.target.value })}
              required
            >
              <option value="">Selecciona una cuenta</option>
              {assetAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.code} — {account.name}
                </option>
              ))}
            </Select>
          ) : null}
          {!form.supplierInvoiceId ? (
            <>
              <Select
                label="Cuenta del activo"
                value={form.assetAccountId}
                onChange={(e) => setForm({ ...form, assetAccountId: e.target.value })}
                required
              >
                <option value="">Selecciona una cuenta ASSET postable…</option>
                {assetAccounts.map((account) => (
                  <option key={account.id} value={account.id}>{account.code} — {account.name}</option>
                ))}
              </Select>
              <Select
                label="Contrapartida de adquisición"
                value={form.acquisitionOffsetAccountId}
                onChange={(e) => setForm({ ...form, acquisitionOffsetAccountId: e.target.value })}
                required
              >
                <option value="">Selecciona la cuenta que financió la adquisición…</option>
                {(accountsQuery.data ?? []).map((account) => (
                  <option key={account.id} value={account.id}>{account.code} — {account.name}</option>
                ))}
              </Select>
            </>
          ) : null}
          <Select
            label="Cuenta de gasto de depreciación"
            value={form.depreciationExpenseAccountId}
            onChange={(e) => setForm({ ...form, depreciationExpenseAccountId: e.target.value })}
            required
          >
            <option value="">Selecciona una cuenta</option>
            {expenseAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} — {account.name}
              </option>
            ))}
          </Select>
          <Select
            label="Cuenta de depreciación acumulada"
            value={form.accumulatedDepreciationAccountId}
            onChange={(e) => setForm({ ...form, accumulatedDepreciationAccountId: e.target.value })}
            required
          >
            <option value="">Selecciona una cuenta</option>
            {assetAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.code} — {account.name}
              </option>
            ))}
          </Select>
          <Button type="submit" loading={createMutation.isPending} disabled={
            !form.supplierInvoiceId && (!form.assetAccountId || !form.acquisitionOffsetAccountId)
          }>
            Guardar
          </Button>
        </form>
      </Modal>

      <Modal
        open={Boolean(depreciationAsset)}
        title={depreciationAsset ? `Depreciación — ${depreciationAsset.name}` : ''}
        onClose={() => setDepreciationAsset(null)}
      >
        {depreciationQuery.isLoading ? (
          <LoadingState label="Cargando…" />
        ) : (
          <>
            <ul>
              {(depreciationQuery.data ?? []).map((entry) => (
                <li key={entry.id}>
                  {entry.periodStart} → {entry.periodEnd}: {entry.amount}{' '}
                  {entry.accountingDocumentId ? '(contabilizado)' : '(sin contabilizar)'}
                </li>
              ))}
              {(depreciationQuery.data ?? []).length === 0 ? <li>Sin periodos depreciados todavía.</li> : null}
            </ul>
            <NewPeriodForm
              onSubmit={(payload) => generateDepreciationMutation.mutate(payload)}
              loading={generateDepreciationMutation.isPending}
              error={generateDepreciationMutation.isError ? String(generateDepreciationMutation.error) : null}
            />
          </>
        )}
      </Modal>

      {disposalAsset ? (
        <AssetDisposalForm
          asset={disposalAsset}
          assetAccounts={assetAccounts}
          loading={disposalMutation.isPending}
          error={disposalMutation.isError ? String(disposalMutation.error) : null}
          onClose={() => setDisposalAsset(null)}
          onSubmit={(payload) => disposalMutation.mutate({ assetId: disposalAsset.id, ...payload })}
        />
      ) : null}
    </div>
  )
}

function AssetDisposalForm({
  asset,
  assetAccounts,
  loading,
  error,
  onClose,
  onSubmit,
}: {
  asset: FixedAsset
  assetAccounts: Array<{ id: string; code: string; name: string }>
  loading: boolean
  error: string | null
  onClose: () => void
  onSubmit: (payload: { disposalDate: string; proceeds: string; proceedsAccountId?: string }) => void
}) {
  const [disposalDate, setDisposalDate] = useState(businessTodayIso())
  const [proceeds, setProceeds] = useState<number | null>(0)
  const [proceedsAccountId, setProceedsAccountId] = useState('')
  const hasProceeds = (proceeds ?? 0) > 0

  return (
    <Modal open title={`Baja contable — ${asset.name}`} onClose={onClose}>
      <form onSubmit={(event) => {
        event.preventDefault()
        onSubmit({
          disposalDate,
          proceeds: String(proceeds ?? 0),
          proceedsAccountId: hasProceeds ? proceedsAccountId : undefined,
        })
      }}>
        <Input label="Fecha económica de la baja" type="date" value={disposalDate} onChange={(event) => setDisposalDate(event.target.value)} required />
        <MoneyInput label={`Ingreso por disposición (${asset.currencyCode})`} value={proceeds} onChange={setProceeds} />
        {hasProceeds ? (
          <Select label="Cuenta de efectivo o por cobrar" value={proceedsAccountId} onChange={(event) => setProceedsAccountId(event.target.value)} required>
            <option value="">Selecciona una cuenta ASSET postable…</option>
            {assetAccounts.map((account) => (
              <option key={account.id} value={account.id}>{account.code} — {account.name}</option>
            ))}
          </Select>
        ) : null}
        <p className="nx-field__hint">
          La baja genera un asiento DIS, retira costo y depreciación acumulada y usa las cuentas configuradas de ganancia o pérdida.
        </p>
        {error ? <p className="nx-field__error" role="alert">{error}</p> : null}
        <Button type="submit" loading={loading} disabled={!disposalDate || (hasProceeds && !proceedsAccountId)}>
          Confirmar baja y contabilizar
        </Button>
      </form>
    </Modal>
  )
}

function NewPeriodForm({
  onSubmit,
  loading,
  error,
}: {
  onSubmit: (payload: { periodStart: string; periodEnd: string }) => void
  loading: boolean
  error: string | null
}) {
  const [periodStart, setPeriodStart] = useState('')
  const [periodEnd, setPeriodEnd] = useState('')
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit({ periodStart, periodEnd })
      }}
    >
      <Input label="Inicio de periodo" type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} required />
      <Input label="Fin de periodo" type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} required />
      <Button type="submit" loading={loading}>
        Generar depreciación del periodo
      </Button>
      {error ? <p className="nx-field__error">{error}</p> : null}
    </form>
  )
}
