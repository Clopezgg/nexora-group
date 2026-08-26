import { useQuery } from '@tanstack/react-query'
import { Badge, Card, EmptyState, ErrorState, LoadingState, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { crmService } from '../../services/crmService'
import type { Opportunity } from '../../types/crm'

export function OpportunitiesPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()

  const opportunitiesQuery = useQuery({
    queryKey: ['crm', 'opportunities', activeCompanyId],
    queryFn: () => crmService.listOpportunities(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const customersQuery = useQuery({
    queryKey: ['crm', 'customers', activeCompanyId],
    queryFn: () => crmService.listCustomers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const customerNameById = new Map((customersQuery.data ?? []).map((c) => [c.id, c.legalName]))

  const columns: TableColumn<Opportunity>[] = [
    { key: 'name', header: 'Oportunidad', render: (row) => row.name },
    {
      key: 'customerId',
      header: 'Cliente',
      render: (row) => customerNameById.get(row.customerId) ?? row.customerId,
    },
    { key: 'stage', header: 'Etapa', render: (row) => <Badge>{row.stage}</Badge> },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return <EmptyState title="Configura una compañía primero" description="No hay compañías registradas todavía." />
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Oportunidades</h1>
      </header>

      <Card>
        {opportunitiesQuery.isLoading ? (
          <LoadingState label="Cargando oportunidades…" />
        ) : opportunitiesQuery.isError ? (
          <ErrorState onRetry={() => opportunitiesQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={opportunitiesQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay oportunidades. Se crean automáticamente al convertir un lead."
          />
        )}
      </Card>
    </div>
  )
}
