import { useState } from 'react'
import { useQuery, useQueries, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, EmptyState, LoadingState, Modal } from '../../design-system'
import { ApiError } from '../../services/httpClient'
import { contractPaymentService } from '../../services/contractPaymentService'
import { procurementService } from '../../services/procurementService'
import { ContractPaymentPlanModal } from '../procurement/ContractPaymentPlanModal'
import { ExecutionContractForm } from '../procurement/ExecutionContractForm'
import {
  SUPPLIER_CONTRACT_CATEGORY_LABELS,
  SUPPLIER_CONTRACT_PAYMENT_TERMS_LABELS,
  type SupplierContract,
} from '../../types/procurement'
import { formatMoney } from '../../utils/currency'

/**
 * Pestaña "Contratos" del Project Cockpit (ORDEN MAESTRA §4/§10/§11/§32).
 * Una tarjeta por contrato de ejecución del proyecto con categoría / valor /
 * pagado / pendiente / próxima cuota — resuelto desde el subledger contractual
 * real, nunca inventado — y las acciones de alta de contrato y de plan de pagos
 * SIN salir del proyecto.
 */
export function ProjectContractsTab({ companyId, projectId }: { companyId: string; projectId: string }) {
  const queryClient = useQueryClient()
  const [addOpen, setAddOpen] = useState(false)
  const [planContract, setPlanContract] = useState<SupplierContract | null>(null)

  const contractsQuery = useQuery({
    queryKey: ['procurement', 'contracts', companyId],
    queryFn: () => procurementService.listContracts(companyId),
    enabled: Boolean(companyId),
  })
  const projectContracts = (contractsQuery.data ?? []).filter((c) => c.projectId === projectId)

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

  const addButton = (
    <Button onClick={() => setAddOpen(true)}>+ Agregar contrato</Button>
  )

  if (contractsQuery.isLoading) return <LoadingState label="Cargando contratos…" />

  return (
    <div className="nx-project-contracts">
      <div className="nx-treasury__actions">{addButton}</div>

      {projectContracts.length === 0 ? (
        <EmptyState
          icon="file"
          title="Este proyecto no tiene contratos de ejecución"
          description="Agrega un contrato de subcontrato, mano de obra, materiales o servicios. Quedará asociado a este proyecto automáticamente."
        />
      ) : (
        projectContracts.map((contract, index) => {
          const schedule = scheduleQueries[index]?.data
          const summary = summaryQueries[index]?.data
          const noSchedule =
            scheduleQueries[index]?.error instanceof ApiError &&
            (scheduleQueries[index]?.error as ApiError).status === 404
          const currency = summary?.currencyCode ?? contract.currencyCode
          const requiresPlan = contract.paymentTermsType !== 'LUMP_SUM' && noSchedule
          return (
            <article key={contract.id} className="nx-project-contracts__card">
              <header>
                <strong>{contract.contractNumber}</strong>
                <Badge tone="neutral">
                  {SUPPLIER_CONTRACT_CATEGORY_LABELS[contract.contractCategory] ??
                    contract.contractCategory}
                </Badge>
              </header>
              <dl>
                <div><dt>Valor contractual</dt><dd>{formatMoney(contract.value, currency)}</dd></div>
                <div>
                  <dt>Esquema de pago</dt>
                  <dd>
                    {SUPPLIER_CONTRACT_PAYMENT_TERMS_LABELS[contract.paymentTermsType] ??
                      contract.paymentTermsType}
                  </dd>
                </div>
                <div>
                  <dt>Pagado acumulado</dt>
                  <dd>{summary ? formatMoney(summary.paidAccumulated, currency) : '—'}</dd>
                </div>
                <div>
                  <dt>Pendiente</dt>
                  <dd>{summary ? formatMoney(summary.contractBalance, currency) : '—'}</dd>
                </div>
                <div>
                  <dt>Próxima cuota</dt>
                  <dd>
                    {noSchedule
                      ? contract.paymentTermsType === 'LUMP_SUM'
                        ? 'Pago único (sin plan)'
                        : 'Sin plan de pagos'
                      : summary?.nextDuePeriod
                        ? `${summary.nextDuePeriod} · ${formatMoney(summary.nextDueAmount ?? '0', currency)}`
                        : schedule
                          ? 'Plan completado'
                          : '—'}
                  </dd>
                </div>
              </dl>
              {requiresPlan ? (
                <p className="nx-field__error" role="alert">
                  Este contrato requiere un plan de pagos antes de poder pagar cuotas.
                </p>
              ) : null}
              <div className="nx-treasury__actions">
                <Button variant="secondary" onClick={() => setPlanContract(contract)}>
                  {noSchedule && contract.paymentTermsType !== 'LUMP_SUM'
                    ? 'Crear plan de pagos'
                    : 'Ver plan de pagos'}
                </Button>
              </div>
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
    </div>
  )
}
