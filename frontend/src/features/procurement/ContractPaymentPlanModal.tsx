import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Modal,
  Select,
  Table,
  Textarea,
  type TableColumn,
} from '../../design-system'
import { ApiError } from '../../services/httpClient'
import {
  contractPaymentService,
  type ContractInstallment,
  type SchedulePlanSnapshot,
} from '../../services/contractPaymentService'
import { apService } from '../../services/apArService'
import { masterDataService } from '../../services/masterDataService'
import { procurementService } from '../../services/procurementService'
import { treasuryService } from '../../services/treasuryService'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import {
  CreateSupplierInvoiceModal,
  PaySupplierInvoiceButton,
} from '../treasury/SupplierInvoiceFlows'
import { formatMoney } from '../../utils/currency'
import { businessTodayIso } from '../../utils/businessDate'
import {
  contractInstallmentKindLabel,
  contractInstallmentStatusLabel,
} from '../../utils/statusLabels'
import type { SupplierContract } from '../../types/procurement'

const STATUS_TONE: Record<string, 'neutral' | 'warning' | 'danger' | 'success'> = {
  PAID: 'success', PARTIALLY_PAID: 'warning', OVERDUE: 'danger', DUE: 'warning', UPCOMING: 'neutral', CANCELLED: 'neutral',
}

export function ContractPaymentPlanModal({ contract, currencyCode, onClose }: {
  contract: SupplierContract
  currencyCode: string
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const nowMonth = businessTodayIso().slice(0, 7)
  const [form, setForm] = useState({ firstPeriod: nowMonth, regularMonths: '7', dueDay: '1' })
  const [prepare, setPrepare] = useState<ContractInstallment | null>(null)

  const { activeCompanyId } = useActiveCompany()

  const scheduleQuery = useQuery({
    queryKey: ['contract-payments', 'by-contract', contract.id],
    queryFn: () => contractPaymentService.getByContract(contract.id),
    retry: false,
    enabled: Boolean(contract.id),
  })
  const scheduleId = scheduleQuery.data?.id
  const summaryQuery = useQuery({
    queryKey: ['contract-payments', 'summary', scheduleId],
    queryFn: () => contractPaymentService.summary(scheduleId as string),
    enabled: Boolean(scheduleId),
  })

  // Queries needed for payment actions
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

  const createMutation = useMutation({
    mutationFn: () => contractPaymentService.createContractPlan({
      supplierContractId: contract.id,
      regularMonths: Number(form.regularMonths),
      dueDay: Number(form.dueDay),
      firstPeriod: `${form.firstPeriod}-01`,
      advanceAmount: contract.advanceAmount ?? undefined,
      advanceDueDate: contract.advanceDueDate ?? undefined,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contract-payments'] })
      queryClient.invalidateQueries({ queryKey: ['procurement', 'contracts'] })
      queryClient.invalidateQueries({ queryKey: ['project'] })
    },
  })

  const notFound = scheduleQuery.error instanceof ApiError && scheduleQuery.error.status === 404
  const currency = scheduleQuery.data?.currencyCode ?? currencyCode

  // Build a map of installmentId → active invoice (not CANCELLED)
  const invoiceByInstallment = new Map(
    (invoicesQuery.data ?? [])
      .filter((inv) => inv.contractInstallmentId && inv.status !== 'CANCELLED')
      .map((inv) => [inv.contractInstallmentId as string, inv]),
  )

  const invalidateAfterPayment = () => {
    queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-invoices'] })
    queryClient.invalidateQueries({ queryKey: ['treasury', 'accounts'] })
    queryClient.invalidateQueries({ queryKey: ['contract-payments'] })
    queryClient.invalidateQueries({ queryKey: ['project'] })
    queryClient.invalidateQueries({ queryKey: ['reports', 'contract-payment-ledger'] })
    queryClient.invalidateQueries({ queryKey: ['contract-payment-ledger'] })
    queryClient.invalidateQueries({ queryKey: ['procurement', 'contracts'] })
  }

  const actionColumn: TableColumn<ContractInstallment> = {
    key: 'actions',
    header: 'Acción',
    render: (r) => {
      // Backend is authority — never allow payment if payableNow=false
      if (!r.payableNow) {
        const isUpcoming = r.status === 'UPCOMING'
        const reason = r.paymentBlockedReason
        return (
          <span
            className="nx-field__hint"
            title={reason ?? (isUpcoming ? 'Cuota futura — aún no pagable' : 'Pago bloqueado')}
            aria-label={reason ?? (isUpcoming ? 'Cuota futura' : 'Bloqueada')}
          >
            {isUpcoming ? 'Próxima' : reason ? 'Bloqueada' : '—'}
          </span>
        )
      }
      if (r.status === 'PAID' || r.status === 'CANCELLED') return null

      const invoice = invoiceByInstallment.get(r.installmentId)
      if (invoice && ['APPROVED', 'SCHEDULED', 'PARTIALLY_PAID'].includes(invoice.status)) {
        const invoiceRemaining = invoice.amount + invoice.taxAmount - invoice.amountPaid
        return (
          <div className="nx-treasury__actions">
            <PaySupplierInvoiceButton
              invoice={invoice}
              companyId={activeCompanyId!}
              treasuryAccounts={treasuryAccountsQuery.data ?? []}
              remaining={invoiceRemaining}
              selectedInstallmentId={r.installmentId}
              label={`Pagar`}
            />
            <PaySupplierInvoiceButton
              invoice={invoice}
              companyId={activeCompanyId!}
              treasuryAccounts={treasuryAccountsQuery.data ?? []}
              remaining={invoiceRemaining}
              selectedInstallmentId={r.installmentId}
              label={`Liquidar`}
              lockAmount
            />
          </div>
        )
      }

      // No invoice yet — open CreateSupplierInvoiceModal pre-linked to this installment
      return (
        <div className="nx-treasury__actions">
          <Button variant="ghost" onClick={() => setPrepare(r)}>
            Pagar
          </Button>
          <Button variant="secondary" onClick={() => setPrepare(r)}>
            Liquidar
          </Button>
        </div>
      )
    },
  }

  const columns: TableColumn<ContractInstallment>[] = [
    {
      key: 'kind', header: 'Tipo', render: (r) => (
        <Badge tone={r.installmentKind === 'ADVANCE' ? 'info' : 'neutral'}>{contractInstallmentKindLabel(r.installmentKind)}</Badge>
      ),
    },
    { key: 'n', header: '#', render: (r) => (r.installmentKind === 'REGULAR' ? String(r.regularNumber) : '—') },
    { key: 'due', header: 'Vencimiento', render: (r) => r.dueDate },
    { key: 'sched', header: 'Programado', numeric: true, render: (r) => formatMoney(r.scheduledAmount, currency) },
    { key: 'ret', header: 'Retención', numeric: true, render: (r) => r.retentionAmount !== '0' && r.retentionAmount !== '0.00' ? formatMoney(r.retentionAmount, currency) : '—' },
    { key: 'net', header: 'Neto', numeric: true, render: (r) => formatMoney(r.netDue, currency) },
    { key: 'paid', header: 'Pagado', numeric: true, render: (r) => formatMoney(r.paid, currency) },
    { key: 'rem', header: 'Pendiente', numeric: true, render: (r) => formatMoney(r.remaining, currency) },
    { key: 'status', header: 'Estado', render: (r) => <Badge tone={STATUS_TONE[r.status] ?? 'neutral'}>{contractInstallmentStatusLabel(r.status)}</Badge> },
    actionColumn,
  ]

  return (
    <Modal open title={`Plan de pagos · ${contract.contractNumber}`} onClose={onClose} size="wide">
      {scheduleQuery.isLoading ? <LoadingState label="Cargando plan…" /> : notFound ? (
        <form onSubmit={(event) => { event.preventDefault(); createMutation.mutate() }}>
          <EmptyState
            icon="calendar"
            title="Este contrato aún no tiene plan de pagos"
            description="El anticipo pactado entra al plan automáticamente. El backend calcula con Decimal la base regular, cada cuota y el residuo final; el navegador no replica la aritmética financiera."
          />
          <dl className="nx-voucher-preview">
            <div><dt>Valor contractual</dt><dd>{formatMoney(contract.value, currency)}</dd></div>
            <div><dt>Anticipo pactado</dt><dd>{contract.advanceAmount ? `${formatMoney(contract.advanceAmount, currency)}${contract.advanceDueDate ? ` · vence ${contract.advanceDueDate}` : ''}` : 'Sin anticipo'}</dd></div>
            <div><dt>Cálculo de cuotas</dt><dd>Motor financiero canónico del backend · precisión Decimal</dd></div>
          </dl>
          <Input label="Primer período (mensualidad 1)" type="month" value={form.firstPeriod} onChange={(e) => setForm({ ...form, firstPeriod: e.target.value })} required />
          <Input label="N.º de mensualidades" type="number" min={1} value={form.regularMonths} onChange={(e) => setForm({ ...form, regularMonths: e.target.value })} required />
          <Select label="Día de pago de cada mes" value={form.dueDay} onChange={(e) => setForm({ ...form, dueDay: e.target.value })}>
            {Array.from({ length: 31 }, (_, i) => String(i + 1)).map((d) => <option key={d} value={d}>{d}</option>)}
          </Select>
          <Button type="submit" loading={createMutation.isPending} disabled={!form.firstPeriod || !form.regularMonths}>Crear plan con motor canónico</Button>
          {createMutation.isError ? <p className="nx-field__error" role="alert">{createMutation.error instanceof ApiError ? createMutation.error.message : 'No se pudo crear el plan.'}</p> : null}
        </form>
      ) : scheduleQuery.isError ? <ErrorState onRetry={() => scheduleQuery.refetch()} /> : (
        <>
          {summaryQuery.data ? (
            <dl className="nx-voucher-preview">
              <div><dt>Valor contractual</dt><dd>{formatMoney(summaryQuery.data.contractValue, currency)}</dd></div>
              <div><dt>Anticipo programado</dt><dd>{formatMoney(summaryQuery.data.advanceScheduled, currency)}</dd></div>
              <div><dt>Anticipo pagado</dt><dd>{formatMoney(summaryQuery.data.advancePaid, currency)}</dd></div>
              <div><dt>Base regular</dt><dd>{formatMoney(summaryQuery.data.regularScheduled, currency)}</dd></div>
              <div><dt>Total programado</dt><dd>{formatMoney(summaryQuery.data.totalContractualScheduled, currency)}</dd></div>
              <div><dt>Programado a fecha</dt><dd>{formatMoney(summaryQuery.data.totalScheduledToDate, currency)}</dd></div>
              <div><dt>Pagado acumulado</dt><dd>{formatMoney(summaryQuery.data.paidAccumulated, currency)}</dd></div>
              <div><dt>Saldo contractual</dt><dd>{formatMoney(summaryQuery.data.contractBalance, currency)}</dd></div>
              <div><dt>Retención pendiente</dt><dd>{formatMoney(summaryQuery.data.retentionOutstanding, currency)}</dd></div>
              <div><dt>Retención efectivamente retenida</dt><dd>{formatMoney(summaryQuery.data.retentionWithheld, currency)}</dd></div>
              <div><dt>Retención autorizada</dt><dd>{formatMoney(summaryQuery.data.retentionReleased, currency)}</dd></div>
              <div><dt>Retención pagada</dt><dd>{formatMoney(summaryQuery.data.retentionPaid, currency)}</dd></div>
              <div><dt>Próximo vencimiento</dt><dd>{summaryQuery.data.nextDuePeriod ? `${summaryQuery.data.nextDuePeriod} · ${formatMoney(summaryQuery.data.nextDueAmount ?? '0', currency)}` : '—'}</dd></div>
            </dl>
          ) : null}
          {scheduleId && summaryQuery.data && summaryQuery.data.retentionAvailableToRelease !== '0.00' ? (
            <RetentionReleaseForm
              scheduleId={scheduleId}
              available={summaryQuery.data.retentionAvailableToRelease}
              currency={currency}
              onReleased={() => {
                queryClient.invalidateQueries({ queryKey: ['contract-payments'] })
                queryClient.invalidateQueries({ queryKey: ['reports', 'contract-payment-ledger'] })
              }}
            />
          ) : null}
          <div style={{ overflowX: 'auto' }}>
            <Table columns={columns} rows={scheduleQuery.data?.installments ?? []} getRowKey={(r) => r.installmentId} emptyMessage="El plan no tiene cuotas." />
          </div>
          {scheduleId ? (
            <CorrectPlanSection
              scheduleId={scheduleId}
              contract={contract}
              currency={currency}
              onApplied={() => {
                queryClient.invalidateQueries({ queryKey: ['contract-payments'] })
                queryClient.invalidateQueries({ queryKey: ['procurement', 'contracts'] })
                queryClient.invalidateQueries({ queryKey: ['project'] })
              }}
            />
          ) : null}
        </>
      )}
      {prepare && activeCompanyId ? (
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
          initialContractId={contract.id}
          initialInstallment={{
            installmentId: prepare.installmentId,
            remaining: prepare.remaining,
            dueDate: prepare.dueDate,
            periodLabel: prepare.periodLabel,
          }}
          onClose={() => setPrepare(null)}
          onCreated={() => {
            setPrepare(null)
            invalidateAfterPayment()
          }}
        />
      ) : null}
    </Modal>
  )
}

function RetentionReleaseForm({ scheduleId, available, currency, onReleased }: {
  scheduleId: string
  available: string
  currency: string
  onReleased: () => void
}) {
  const [amount, setAmount] = useState(available)
  const [dueDate, setDueDate] = useState(businessTodayIso())
  const [reason, setReason] = useState('')
  const mutation = useMutation({
    mutationFn: () => contractPaymentService.authorizeRetentionRelease(scheduleId, { amount, dueDate, reason }),
    onSuccess: onReleased,
  })
  return (
    <section className="nx-section" aria-labelledby={`retention-release-${scheduleId}`}>
      <h3 id={`retention-release-${scheduleId}`}>Liberar retención</h3>
      <p>Disponible para autorizar: {formatMoney(available, currency)}. La autorización crea una obligación pagable trazable.</p>
      <form onSubmit={(event) => { event.preventDefault(); mutation.mutate() }}>
        <Input label="Importe a liberar" value={amount} onChange={(event) => setAmount(event.target.value)} inputMode="decimal" required />
        <Input label="Fecha de exigibilidad" type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} required />
        <Textarea label="Motivo de liberación" value={reason} onChange={(event) => setReason(event.target.value)} minLength={10} required />
        <Button type="submit" loading={mutation.isPending} disabled={!amount || !dueDate || reason.trim().length < 10}>
          Autorizar liberación
        </Button>
        {mutation.isError ? <p className="nx-field__error" role="alert">{mutation.error instanceof ApiError ? mutation.error.message : 'No se pudo autorizar la liberación.'}</p> : null}
      </form>
    </section>
  )
}

const SNAPSHOT_COLUMNS: TableColumn<SchedulePlanSnapshot['installments'][number]>[] = [
  { key: 'kind', header: 'Tipo', render: (r) => contractInstallmentKindLabel(r.kind) },
  { key: 'label', header: 'Período', render: (r) => r.periodLabel },
  { key: 'due', header: 'Vencimiento', render: (r) => r.dueDate },
]

function SnapshotTable({ title, snapshot, currency }: { title: string; snapshot: SchedulePlanSnapshot; currency: string }) {
  const columns: TableColumn<SchedulePlanSnapshot['installments'][number]>[] = [
    ...SNAPSHOT_COLUMNS,
    { key: 'sched', header: 'Programado', numeric: true, render: (r) => formatMoney(r.scheduledAmount, currency) },
  ]
  return (
    <div style={{ flex: '1 1 320px', minWidth: 280 }}>
      <p className="nx-field__label">{title} · total {formatMoney(snapshot.totalScheduled, currency)}</p>
      <div style={{ overflowX: 'auto' }}>
        <Table columns={columns} rows={snapshot.installments} getRowKey={(r) => `${r.kind}-${r.periodLabel}-${r.dueDate}`} emptyMessage="Sin cuotas." />
      </div>
    </div>
  )
}

function CorrectPlanSection({ scheduleId, contract, currency, onApplied }: {
  scheduleId: string
  contract: SupplierContract
  currency: string
  onApplied: () => void
}) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [terms, setTerms] = useState({
    firstPeriod: businessTodayIso().slice(0, 7),
    regularMonths: '7',
    dueDay: '1',
    advanceAmount: contract.advanceAmount ?? '',
    advanceDueDate: contract.advanceDueDate ?? '',
    retentionPercentage: contract.retentionPercentage ?? '0',
  })

  const payload = () => ({
    regularMonths: Number(terms.regularMonths),
    dueDay: Number(terms.dueDay),
    firstPeriod: `${terms.firstPeriod}-01`,
    advanceAmount: terms.advanceAmount || undefined,
    advanceDueDate: terms.advanceDueDate || undefined,
    retentionPercentage: terms.retentionPercentage || undefined,
  })
  const previewMutation = useMutation({ mutationFn: () => contractPaymentService.previewRebuild(scheduleId, payload()) })
  const amendmentPreviewMutation = useMutation({ mutationFn: () => contractPaymentService.previewAmendment(scheduleId, payload()) })
  const preview = amendmentPreviewMutation.data ?? previewMutation.data
  const isAmendment = Boolean(amendmentPreviewMutation.data)
  const applyMutation = useMutation({
    mutationFn: () => (isAmendment
      ? contractPaymentService.amendPlan(scheduleId, { ...payload(), reason })
      : contractPaymentService.rebuildPlan(scheduleId, { ...payload(), reason })),
    onSuccess: () => {
      previewMutation.reset()
      amendmentPreviewMutation.reset()
      setOpen(false)
      setReason('')
      onApplied()
    },
  })
  const reasonValid = reason.trim().length >= 10

  if (!open) return <div className="nx-treasury__actions" style={{ marginTop: 16 }}><Button variant="secondary" onClick={() => setOpen(true)}>Corregir plan de pagos</Button></div>

  return (
    <div style={{ marginTop: 16, borderTop: '1px solid var(--nx-color-border, #ddd)', paddingTop: 16 }}>
      <p className="nx-field__label">Corregir / recalcular el plan</p>
      <p className="nx-field__hint">La previsualización ANTES/DESPUÉS proviene del mismo motor Decimal que aplicará el cambio. Requiere motivo y se audita; un plan con pagos aplicados se bloquea.</p>
      <Input label="Primer período (mensualidad 1)" type="month" value={terms.firstPeriod} onChange={(e) => setTerms({ ...terms, firstPeriod: e.target.value })} />
      <Input label="N.º de mensualidades" type="number" min={1} value={terms.regularMonths} onChange={(e) => setTerms({ ...terms, regularMonths: e.target.value })} />
      <Select label="Día de pago de cada mes" value={terms.dueDay} onChange={(e) => setTerms({ ...terms, dueDay: e.target.value })}>
        {Array.from({ length: 31 }, (_, i) => String(i + 1)).map((d) => <option key={d} value={d}>{d}</option>)}
      </Select>
      <Input label="Anticipo (monto)" value={terms.advanceAmount} onChange={(e) => setTerms({ ...terms, advanceAmount: e.target.value })} placeholder="0.00" />
      <Input label="Vencimiento del anticipo" type="date" value={terms.advanceDueDate} onChange={(e) => setTerms({ ...terms, advanceDueDate: e.target.value })} />
      <Input label="Retención (%)" value={terms.retentionPercentage} onChange={(e) => setTerms({ ...terms, retentionPercentage: e.target.value })} />
      <div className="nx-treasury__actions">
        <Button variant="secondary" loading={previewMutation.isPending || amendmentPreviewMutation.isPending} onClick={() => { amendmentPreviewMutation.reset(); previewMutation.mutate() }}>Previsualizar cambios</Button>
        <Button variant="secondary" onClick={() => { setOpen(false); previewMutation.reset() }}>Cancelar</Button>
      </div>
      {previewMutation.isError ? <p className="nx-field__error" role="alert">{previewMutation.error instanceof ApiError ? previewMutation.error.message : 'No se pudo previsualizar.'}</p> : null}
      {amendmentPreviewMutation.isError ? <p className="nx-field__error" role="alert">{amendmentPreviewMutation.error instanceof ApiError ? amendmentPreviewMutation.error.message : 'No se pudo previsualizar la enmienda.'}</p> : null}
      {preview ? <>
        {preview.blocked ? <div className="nx-field__error" role="alert"><p>{preview.blockedReason ?? 'El plan tiene pagos aplicados; no puede recalcularse.'}</p><Button variant="secondary" loading={amendmentPreviewMutation.isPending} onClick={() => amendmentPreviewMutation.mutate()}>Previsualizar enmienda formal</Button></div> : null}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, marginTop: 12 }}>
          <SnapshotTable title="ANTES" snapshot={preview.before} currency={currency} />
          {preview.after ? <SnapshotTable title="DESPUÉS" snapshot={preview.after} currency={currency} /> : null}
        </div>
        {(!preview.blocked || isAmendment) ? <>
          <label className="nx-field" style={{ marginTop: 12 }}>
            <span className="nx-field__label">Motivo de la {isAmendment ? 'enmienda formal' : 'corrección'} (obligatorio)</span>
            <textarea className="nx-input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} placeholder={isAmendment ? 'Por qué se enmienda el plan (mínimo 10 caracteres)' : 'Por qué se corrige el plan (mínimo 10 caracteres)'} />
          </label>
          <div className="nx-treasury__actions"><Button loading={applyMutation.isPending} disabled={!reasonValid} onClick={() => applyMutation.mutate()}>{isAmendment ? 'Aplicar enmienda formal' : 'Aplicar corrección'}</Button></div>
          {applyMutation.isError ? <p className="nx-field__error" role="alert">{applyMutation.error instanceof ApiError ? applyMutation.error.message : 'No se pudo aplicar la corrección.'}</p> : null}
        </> : null}
      </> : null}
    </div>
  )
}
