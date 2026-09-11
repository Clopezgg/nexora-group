import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueries, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, EmptyState, LoadingState, Modal } from '../../design-system'
import { ApiError } from '../../services/httpClient'
import { contractPaymentService } from '../../services/contractPaymentService'
import { procurementService } from '../../services/procurementService'
import { masterDataService } from '../../services/masterDataService'
import { treasuryService } from '../../services/treasuryService'
import { apService } from '../../services/apArService'
import { ContractPaymentPlanModal } from '../procurement/ContractPaymentPlanModal'
import { ExecutionContractForm } from '../procurement/ExecutionContractForm'
import { CreateSupplierInvoiceModal, PaySupplierInvoiceButton } from '../treasury/SupplierInvoiceFlows'
import {
  SUPPLIER_CONTRACT_CATEGORY_LABELS,
  SUPPLIER_CONTRACT_PAYMENT_TERMS_LABELS,
  type SupplierContract,
} from '../../types/procurement'
import { formatMoney } from '../../utils/currency'
import { statusLabel, supplierPartyRoleLabel } from '../../utils/statusLabels'

/** Project Contract Command Center: contrato → obligación → pago → Treasury/GL. */
export function ProjectContractsTab({ companyId, projectId }: { companyId: string; projectId: string }) {
  const queryClient = useQueryClient()
  const [addOpen, setAddOpen] = useState(false)
  const [planContract, setPlanContract] = useState<SupplierContract | null>(null)
  const [obligationContract, setObligationContract] = useState<SupplierContract | null>(null)

  const contractsQuery = useQuery({
    queryKey: ['procurement', 'contracts', companyId],
    queryFn: () => procurementService.listContracts(companyId),
    enabled: Boolean(companyId),
  })
  const suppliersQuery = useQuery({
    queryKey: ['procurement', 'suppliers', companyId],
    queryFn: () => procurementService.listSuppliers(companyId),
    enabled: Boolean(companyId),
  })
  const invoicesQuery = useQuery({
    queryKey: ['ap', 'supplier-invoices', companyId],
    queryFn: () => apService.listInvoices(companyId),
    enabled: Boolean(companyId),
  })
  const accountsQuery = useQuery({
    queryKey: ['master-data', 'accounts', companyId],
    queryFn: () => masterDataService.listAccounts(companyId),
    enabled: Boolean(companyId),
  })
  const treasuryAccountsQuery = useQuery({
    queryKey: ['treasury', 'accounts', companyId],
    queryFn: () => treasuryService.listAccounts(companyId),
    enabled: Boolean(companyId),
  })

  const projectContracts = (contractsQuery.data ?? []).filter((c) => c.projectId === projectId)
  const supplierById = new Map((suppliersQuery.data ?? []).map((s) => [s.id, s]))
  const expenseAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'EXPENSE' || a.accountType === 'ASSET')
  const payableAccounts = (accountsQuery.data ?? []).filter((a) => a.accountType === 'LIABILITY')
  const treasuryAccounts = treasuryAccountsQuery.data ?? []

  const scheduleQueries = useQueries({
    queries: projectContracts.map((contract) => ({
      queryKey: ['contract-payments', 'by-contract', contract.id],
      queryFn: () => contractPaymentService.getByContract(contract.id),
      retry: false,
    })),
  })
  const summaryQueries = useQueries({
    queries: scheduleQueries.map((sq, index) => ({
      queryKey: ['contract-payments', 'summary', sq.data?.id, projectContracts[index]?.id],
      queryFn: () => contractPaymentService.summary(sq.data!.id),
      enabled: Boolean(sq.data?.id),
    })),
  })
  const obligationContractIndex = obligationContract
    ? projectContracts.findIndex((contract) => contract.id === obligationContract.id)
    : -1
  const obligationInstallment = obligationContractIndex >= 0
    ? scheduleQueries[obligationContractIndex]?.data?.installments.find(
        (row) => !['PAID', 'CANCELLED'].includes(row.status),
      ) ?? null
    : null

  if (contractsQuery.isLoading) return <LoadingState label="Cargando contratos…" />

  return (
    <div className="nx-project-contracts">
      <div className="nx-treasury__actions">
        <Button onClick={() => setAddOpen(true)}>+ Agregar contrato</Button>
        <Link to="/finanzas/libro-contractual">Abrir libro contractual</Link>
      </div>

      {projectContracts.length === 0 ? (
        <EmptyState
          icon="file"
          title="Este proyecto no tiene contratos de ejecución"
          description="Agrega mano de obra, subcontrato, materiales o servicios. Desde aquí podrás preparar la obligación y pagarla sin perder el contexto del proyecto."
        />
      ) : (
        projectContracts.map((contract, index) => {
          const schedule = scheduleQueries[index]?.data
          const summary = summaryQueries[index]?.data
          const noSchedule = scheduleQueries[index]?.error instanceof ApiError && (scheduleQueries[index]?.error as ApiError).status === 404
          const currency = summary?.currencyCode ?? contract.currencyCode
          const requiresPlan = contract.paymentTermsType !== 'LUMP_SUM' && noSchedule
          const party = supplierById.get(contract.supplierId)
          const nextInstallment = schedule?.installments.find((row) => !['PAID', 'CANCELLED'].includes(row.status)) ?? null
          const invoices = (invoicesQuery.data ?? []).filter((invoice) => invoice.supplierContractId === contract.id && invoice.status !== 'CANCELLED')
          const payableInvoice = invoices.find((invoice) => ['APPROVED', 'SCHEDULED', 'PARTIALLY_PAID'].includes(invoice.status)) ?? null
          const pendingInvoice = invoices.find((invoice) => ['DRAFT', 'REVIEW'].includes(invoice.status)) ?? null
          const remaining = payableInvoice ? payableInvoice.amount + payableInvoice.taxAmount - payableInvoice.amountPaid : 0

          return (
            <article key={contract.id} className="nx-project-contracts__card">
              <header>
                <div>
                  <strong>{contract.contractNumber}</strong>
                  <p className="nx-field__hint">
                    {party ? `${supplierPartyRoleLabel(party.partyRole)} · ${party.tradeName || party.legalName}` : 'Tercero no disponible'}
                  </p>
                </div>
                <Badge tone="neutral">{SUPPLIER_CONTRACT_CATEGORY_LABELS[contract.contractCategory] ?? contract.contractCategory}</Badge>
              </header>
              <dl>
                <div><dt>Valor contractual</dt><dd>{formatMoney(contract.value, currency)}</dd></div>
                <div><dt>Anticipo pactado</dt><dd>{formatMoney(contract.advanceAmount ?? '0', currency)}</dd></div>
                <div><dt>Pagado acumulado</dt><dd>{summary ? formatMoney(summary.paidAccumulated, currency) : '—'}</dd></div>
                <div><dt>Saldo contractual</dt><dd>{summary ? formatMoney(summary.contractBalance, currency) : '—'}</dd></div>
                <div><dt>Esquema</dt><dd>{SUPPLIER_CONTRACT_PAYMENT_TERMS_LABELS[contract.paymentTermsType] ?? contract.paymentTermsType}</dd></div>
                <div>
                  <dt>Próxima obligación</dt>
                  <dd>
                    {nextInstallment
                      ? `${nextInstallment.periodLabel} · vence ${nextInstallment.dueDate} · ${formatMoney(nextInstallment.remaining, currency)}`
                      : noSchedule
                        ? contract.paymentTermsType === 'LUMP_SUM' ? 'Pago único (sin plan)' : 'Sin plan de pagos'
                        : schedule ? 'Plan completado' : '—'}
                  </dd>
                </div>
              </dl>

              {requiresPlan ? <p className="nx-field__error" role="alert">Crea el plan antes de preparar o pagar una cuota.</p> : null}
              {pendingInvoice ? (
                <p className="nx-field__hint">
                  Obligación {pendingInvoice.invoiceNumber}: {statusLabel(pendingInvoice.status)}. Debe completar aprobación antes del pago.{' '}
                  <Link to="/finanzas/cuentas-por-pagar">Abrir aprobación/AP</Link>
                </p>
              ) : null}

              <div className="nx-treasury__actions">
                <Button variant="secondary" onClick={() => setPlanContract(contract)}>
                  {noSchedule && contract.paymentTermsType !== 'LUMP_SUM' ? 'Crear plan de pagos' : 'Ver plan de pagos'}
                </Button>
                {!requiresPlan && !payableInvoice && !pendingInvoice ? (
                  <Button
                    variant="secondary"
                    onClick={() => setObligationContract(contract)}
                    disabled={expenseAccounts.length === 0 || payableAccounts.length === 0}
                  >
                    Preparar próxima obligación
                  </Button>
                ) : null}
                {payableInvoice ? (
                  <PaySupplierInvoiceButton
                    invoice={payableInvoice}
                    companyId={companyId}
                    treasuryAccounts={treasuryAccounts}
                    remaining={remaining}
                    selectedInstallmentId={nextInstallment?.installmentId}
                    label="Pagar próxima cuota"
                  />
                ) : null}
              </div>
              {!requiresPlan && !payableInvoice && !pendingInvoice && (expenseAccounts.length === 0 || payableAccounts.length === 0) ? (
                <p className="nx-field__error">Configura la cuenta de contrapartida (gasto/activo) y la cuenta por pagar para preparar la obligación.</p>
              ) : null}
            </article>
          )
        })
      )}

      {addOpen ? (
        <Modal open title="Nuevo contrato de ejecución" onClose={() => setAddOpen(false)}>
          <ExecutionContractForm
            lockedProjectId={projectId}
            onCancel={() => setAddOpen(false)}
            onCreated={() => {
              setAddOpen(false)
              queryClient.invalidateQueries({ queryKey: ['procurement', 'contracts', companyId] })
            }}
          />
        </Modal>
      ) : null}

      {planContract ? (
        <ContractPaymentPlanModal
          contract={planContract}
          currencyCode={planContract.currencyCode ?? 'HNL'}
          onClose={() => {
            setPlanContract(null)
            queryClient.invalidateQueries({ queryKey: ['contract-payments'] })
          }}
        />
      ) : null}

      {obligationContract ? (
        <CreateSupplierInvoiceModal
          companyId={companyId}
          expenseAccounts={expenseAccounts}
          payableAccounts={payableAccounts}
          suppliers={(suppliersQuery.data ?? []).map((s) => ({ id: s.id, legalName: s.legalName }))}
          contracts={projectContracts}
          initialContractId={obligationContract.id}
          initialInstallment={obligationInstallment ? {
            installmentId: obligationInstallment.installmentId,
            remaining: obligationInstallment.remaining,
            dueDate: obligationInstallment.dueDate,
            periodLabel: obligationInstallment.periodLabel,
          } : undefined}
          lockedProjectId={projectId}
          onClose={() => setObligationContract(null)}
          onCreated={() => {
            setObligationContract(null)
            queryClient.invalidateQueries({ queryKey: ['ap', 'supplier-invoices', companyId] })
          }}
        />
      ) : null}
    </div>
  )
}
