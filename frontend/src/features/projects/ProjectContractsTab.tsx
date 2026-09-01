import { useQuery, useQueries } from '@tanstack/react-query'
import { Badge, EmptyState, LoadingState } from '../../design-system'
import { ApiError } from '../../services/httpClient'
import { contractPaymentService } from '../../services/contractPaymentService'
import { procurementService } from '../../services/procurementService'
import { SUPPLIER_CONTRACT_CATEGORY_LABELS } from '../../types/procurement'
import { formatMoney } from '../../utils/currency'

/**
 * Pestaña "Contratos" del Project Cockpit (ORDEN MAESTRA §19). Una tarjeta por
 * contrato de ejecución del proyecto con: categoría / valor / pagado /
 * pendiente / próxima cuota — resuelto desde el subledger contractual real,
 * nunca inventado.
 */
export function ProjectContractsTab({ companyId, projectId }: { companyId: string; projectId: string }) {
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

  if (contractsQuery.isLoading) return <LoadingState label="Cargando contratos…" />
  if (projectContracts.length === 0) {
    return (
      <EmptyState
        icon="file"
        title="Este proyecto no tiene contratos de ejecución"
        description="Registra un contrato de subcontrato o mano de obra desde Abastecimiento → Contratos y asígnalo a este proyecto."
      />
    )
  }

  return (
    <div className="nx-project-contracts">
      {projectContracts.map((contract, index) => {
        const schedule = scheduleQueries[index]?.data
        const summary = summaryQueries[index]?.data
        const noSchedule =
          scheduleQueries[index]?.error instanceof ApiError &&
          (scheduleQueries[index]?.error as ApiError).status === 404
        const currency = summary?.currencyCode ?? contract.currencyCode
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
                    ? 'Sin plan de pagos'
                    : summary?.nextDuePeriod
                      ? `${summary.nextDuePeriod} · ${formatMoney(summary.nextDueAmount ?? '0', currency)}`
                      : schedule
                        ? 'Plan completado'
                        : '—'}
                </dd>
              </div>
            </dl>
          </article>
        )
      })}
    </div>
  )
}
