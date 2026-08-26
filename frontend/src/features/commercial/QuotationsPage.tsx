import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Modal,
  MoneyInput,
  ProjectSelector,
  Table,
} from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { crmService } from '../../services/crmService'
import { projectService } from '../../services/projectService'
import type { Opportunity, Quotation } from '../../types/crm'

export function QuotationsPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const [modalOpen, setModalOpen] = useState(false)
  const queryClient = useQueryClient()

  const quotationsQuery = useQuery({
    queryKey: ['crm', 'quotations', activeCompanyId],
    queryFn: () => crmService.listQuotations(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const opportunitiesQuery = useQuery({
    queryKey: ['crm', 'opportunities', activeCompanyId],
    queryFn: () => crmService.listOpportunities(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['crm', 'quotations', activeCompanyId] })
    queryClient.invalidateQueries({ queryKey: ['crm', 'sales-contracts', activeCompanyId] })
  }

  const acceptMutation = useMutation({
    mutationFn: (id: string) => crmService.acceptQuotation(id),
    onSuccess: invalidate,
  })

  const convertMutation = useMutation({
    mutationFn: (quotation: Quotation) =>
      crmService.convertQuotation(quotation.id, {
        contractNumber: `SC-${quotation.quotationNumber}`,
        startDate: new Date().toISOString().slice(0, 10),
      }),
    onSuccess: invalidate,
  })

  const opportunities = opportunitiesQuery.data ?? []

  const columns: TableColumn<Quotation>[] = [
    { key: 'quotationNumber', header: 'Cotización', render: (row) => row.quotationNumber },
    { key: 'amount', header: 'Monto', render: (row) => `${row.currencyCode} ${row.amount}` },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{row.status}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <div className="nx-treasury__actions">
          {['DRAFT', 'SENT'].includes(row.status) ? (
            <Button
              variant="secondary"
              loading={acceptMutation.isPending}
              onClick={() => acceptMutation.mutate(row.id)}
            >
              Aceptar
            </Button>
          ) : null}
          {row.status === 'ACCEPTED' ? (
            <Button
              variant="secondary"
              loading={convertMutation.isPending}
              onClick={() => convertMutation.mutate(row)}
            >
              Convertir a contrato
            </Button>
          ) : null}
        </div>
      ),
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return <EmptyState title="Configura una compañía primero" description="No hay compañías registradas todavía." />
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Cotizaciones</h1>
        <Button onClick={() => setModalOpen(true)} disabled={opportunities.length === 0}>
          Nueva cotización
        </Button>
      </header>

      {opportunities.length === 0 ? (
        <p className="nx-field__error">
          Necesitas al menos una oportunidad (Comercial → Leads → Convertir a cliente).
        </p>
      ) : null}

      <Card>
        {quotationsQuery.isLoading ? (
          <LoadingState label="Cargando cotizaciones…" />
        ) : quotationsQuery.isError ? (
          <ErrorState onRetry={() => quotationsQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={quotationsQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay cotizaciones registradas."
          />
        )}
      </Card>

      {modalOpen && activeCompanyId ? (
        <CreateQuotationModal
          companyId={activeCompanyId}
          opportunities={opportunities}
          onClose={() => setModalOpen(false)}
          onCreated={invalidate}
        />
      ) : null}
    </div>
  )
}

function CreateQuotationModal({
  companyId,
  opportunities,
  onClose,
  onCreated,
}: {
  companyId: string
  opportunities: Opportunity[]
  onClose: () => void
  onCreated: () => void
}) {
  const [opportunityId, setOpportunityId] = useState<string | null>(opportunities[0]?.id ?? null)
  const [projectId, setProjectId] = useState<string | null>(null)
  const [quotationNumber, setQuotationNumber] = useState('')
  const [amount, setAmount] = useState<number | null>(null)

  const projectsQuery = useQuery({
    queryKey: ['projects', companyId],
    queryFn: () => projectService.list(companyId),
  })
  const projectOptions = (projectsQuery.data ?? []).map((p) => ({ id: p.id, label: p.name }))

  const selectedOpportunity = opportunities.find((o) => o.id === opportunityId) ?? null

  const mutation = useMutation({
    mutationFn: () =>
      crmService.createQuotation({
        companyId,
        opportunityId: opportunityId as string,
        customerId: selectedOpportunity?.customerId as string,
        projectId: projectId ?? undefined,
        quotationNumber,
        amount: String(amount ?? 0),
        currencyCode: 'HNL',
      }),
    onSuccess: () => {
      onCreated()
      onClose()
    },
  })

  return (
    <Modal open title="Nueva cotización" onClose={onClose}>
      <form
        className="nx-treasury__form"
        onSubmit={(event) => {
          event.preventDefault()
          mutation.mutate()
        }}
      >
        <label className="nx-field">
          <span className="nx-field__label">Oportunidad</span>
          <select
            className="nx-input"
            value={opportunityId ?? ''}
            onChange={(e) => setOpportunityId(e.target.value)}
          >
            {opportunities.map((o) => (
              <option key={o.id} value={o.id}>
                {o.name}
              </option>
            ))}
          </select>
        </label>
        <ProjectSelector
          options={projectOptions}
          value={projectId}
          onChange={setProjectId}
          disabled={projectOptions.length === 0}
        />
        <label className="nx-field">
          <span className="nx-field__label">Número de cotización</span>
          <input
            className="nx-input"
            value={quotationNumber}
            onChange={(e) => setQuotationNumber(e.target.value)}
            required
          />
        </label>
        <MoneyInput label="Monto (HNL)" value={amount} onChange={setAmount} />
        {mutation.isError ? (
          <p className="nx-field__error">{(mutation.error as Error).message}</p>
        ) : null}
        <Button
          type="submit"
          loading={mutation.isPending}
          disabled={!amount || !opportunityId || !quotationNumber}
        >
          Registrar
        </Button>
      </form>
    </Modal>
  )
}
