import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { inventoryService } from '../../services/inventoryService'
import type { Item } from '../../types/inventory'

export function InventoryPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const [sku, setSku] = useState('')
  const [name, setName] = useState('')
  const queryClient = useQueryClient()

  const itemsQuery = useQuery({
    queryKey: ['inventory', 'items', activeCompanyId],
    queryFn: () => inventoryService.listItems(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const createMutation = useMutation({
    mutationFn: () => inventoryService.createItem({ companyId: activeCompanyId as string, sku, name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['inventory', 'items', activeCompanyId] })
      setSku('')
      setName('')
    },
  })

  const columns: TableColumn<Item>[] = [
    { key: 'sku', header: 'SKU', render: (row) => row.sku },
    { key: 'name', header: 'Nombre', render: (row) => row.name },
    { key: 'uom', header: 'UOM', render: (row) => row.uom },
    { key: 'active', header: 'Estado', render: (row) => <Badge>{row.active ? 'Activo' : 'Inactivo'}</Badge> },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return <EmptyState title="Configura una compañía primero" description="No hay compañías registradas todavía." />
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Inventario</h1>
      </header>

      <Card title="Nuevo ítem">
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input label="SKU" value={sku} onChange={(e) => setSku(e.target.value)} required />
          <Input label="Nombre" value={name} onChange={(e) => setName(e.target.value)} required />
          <Button type="submit" loading={createMutation.isPending} disabled={!sku || !name}>
            Crear ítem
          </Button>
        </form>
      </Card>

      <Card title="Ítems">
        {itemsQuery.isLoading ? (
          <LoadingState label="Cargando ítems…" />
        ) : itemsQuery.isError ? (
          <ErrorState onRetry={() => itemsQuery.refetch()} />
        ) : (
          <Table columns={columns} rows={itemsQuery.data ?? []} getRowKey={(row) => row.id} emptyMessage="Aún no hay ítems registrados." />
        )}
      </Card>
    </div>
  )
}
