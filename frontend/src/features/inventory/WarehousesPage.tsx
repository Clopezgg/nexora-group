import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { inventoryService } from '../../services/inventoryService'
import type { Warehouse } from '../../types/inventory'

export function WarehousesPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const handleMutationError = useMutationError()
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const queryClient = useQueryClient()

  const warehousesQuery = useQuery({
    queryKey: ['inventory', 'warehouses', activeCompanyId],
    queryFn: () => inventoryService.listWarehouses(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const createMutation = useMutation({
    mutationFn: () => inventoryService.createWarehouse({ companyId: activeCompanyId as string, code, name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory', 'warehouses', activeCompanyId] })
      setCode('')
      setName('')
    },
    onError: (error) => handleMutationError(error, 'Crear almacén'),
  })

  const columns: TableColumn<Warehouse>[] = [
    { key: 'code', header: 'Código', render: (row) => row.code },
    { key: 'name', header: 'Nombre', render: (row) => row.name },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{row.status}</Badge> },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return <EmptyState title="Configura una compañía primero" description="No hay compañías registradas todavía." />
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Almacenes</h1>
      </header>

      <Card title="Nuevo almacén">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input label="Código" value={code} onChange={(e) => setCode(e.target.value)} required />
          <Input label="Nombre" value={name} onChange={(e) => setName(e.target.value)} required />
          <Button type="submit" loading={createMutation.isPending} disabled={!code || !name}>
            Crear almacén
          </Button>
        </form>
      </Card>

      <Card title="Almacenes">
        {warehousesQuery.isLoading ? (
          <LoadingState label="Cargando almacenes…" />
        ) : warehousesQuery.isError ? (
          <ErrorState onRetry={() => warehousesQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={warehousesQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay almacenes registrados."
          />
        )}
      </Card>
    </div>
  )
}
