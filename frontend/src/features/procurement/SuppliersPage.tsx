import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, Modal, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { procurementService } from '../../services/procurementService'
import type { Supplier } from '../../types/procurement'

export function SuppliersPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const handleMutationError = useMutationError()
  const [modalOpen, setModalOpen] = useState(false)
  const [legalName, setLegalName] = useState('')
  const [taxId, setTaxId] = useState('')
  const queryClient = useQueryClient()

  const suppliersQuery = useQuery({
    queryKey: ['procurement', 'suppliers', activeCompanyId],
    queryFn: () => procurementService.listSuppliers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      procurementService.createSupplier({ companyId: activeCompanyId as string, legalName, taxId: taxId || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'suppliers', activeCompanyId] })
      setModalOpen(false)
      setLegalName('')
      setTaxId('')
    },
    onError: (error) => handleMutationError(error, 'Crear proveedor'),
  })

  const columns: TableColumn<Supplier>[] = [
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
        <h1 className="nx-dashboard__title">Proveedores</h1>
        <Button onClick={() => setModalOpen(true)}>Nuevo proveedor</Button>
      </header>

      <Card>
        {suppliersQuery.isLoading ? (
          <LoadingState label="Cargando proveedores…" />
        ) : suppliersQuery.isError ? (
          <ErrorState onRetry={() => suppliersQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={suppliersQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay proveedores registrados."
          />
        )}
      </Card>

      <Modal open={modalOpen} title="Nuevo proveedor" onClose={() => setModalOpen(false)}>
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
