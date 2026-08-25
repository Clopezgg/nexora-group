import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, Modal, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { crmService } from '../../services/crmService'
import type { Customer } from '../../types/crm'

export function CustomersPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const [modalOpen, setModalOpen] = useState(false)
  const [legalName, setLegalName] = useState('')
  const [taxId, setTaxId] = useState('')
  const queryClient = useQueryClient()

  const customersQuery = useQuery({
    queryKey: ['crm', 'customers', activeCompanyId],
    queryFn: () => crmService.listCustomers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      crmService.createCustomer({ companyId: activeCompanyId as string, legalName, taxId: taxId || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['crm', 'customers', activeCompanyId] })
      setModalOpen(false)
      setLegalName('')
      setTaxId('')
    },
  })

  const columns: TableColumn<Customer>[] = [
    { key: 'legalName', header: 'Razón social', render: (row) => row.legalName },
    { key: 'taxId', header: 'RTN', render: (row) => row.taxId ?? '—' },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{row.status}</Badge> },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return <EmptyState title="Configura una compañía primero" description="No hay compañías registradas todavía." />
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Clientes</h1>
        <Button onClick={() => setModalOpen(true)}>Nuevo cliente</Button>
      </header>

      <Card>
        {customersQuery.isLoading ? (
          <LoadingState label="Cargando clientes…" />
        ) : customersQuery.isError ? (
          <ErrorState onRetry={() => customersQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={customersQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay clientes registrados. Se crean directamente o al convertir un lead."
          />
        )}
      </Card>

      <Modal open={modalOpen} title="Nuevo cliente" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input label="Razón social" value={legalName} onChange={(e) => setLegalName(e.target.value)} required />
          <Input label="RTN / Tax ID" value={taxId} onChange={(e) => setTaxId(e.target.value)} />
          <Button type="submit" loading={createMutation.isPending} disabled={!legalName}>
            Guardar
          </Button>
        </form>
      </Modal>
    </div>
  )
}
