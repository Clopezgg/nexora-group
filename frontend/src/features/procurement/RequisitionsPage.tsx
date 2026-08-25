import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, Modal, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { procurementService } from '../../services/procurementService'
import type { Requisition } from '../../types/procurement'

export function RequisitionsPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const [modalOpen, setModalOpen] = useState(false)
  const [description, setDescription] = useState('')
  const [quantity, setQuantity] = useState('')
  const [justification, setJustification] = useState('')
  const queryClient = useQueryClient()

  const requisitionsQuery = useQuery({
    queryKey: ['procurement', 'requisitions', activeCompanyId],
    queryFn: () => procurementService.listRequisitions(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      procurementService.createRequisition({
        companyId: activeCompanyId as string,
        justification: justification || undefined,
        lines: [{ description, quantity }],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'requisitions', activeCompanyId] })
      setModalOpen(false)
      setDescription('')
      setQuantity('')
      setJustification('')
    },
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => procurementService.approveRequisition(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['procurement', 'requisitions', activeCompanyId] }),
  })

  const columns: TableColumn<Requisition>[] = [
    { key: 'number', header: 'Número', render: (row) => row.requisitionNumber },
    { key: 'justification', header: 'Justificación', render: (row) => row.justification ?? '—' },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{row.status}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) =>
        row.status === 'SUBMITTED' ? (
          <Button variant="secondary" onClick={() => approveMutation.mutate(row.id)} loading={approveMutation.isPending}>
            Aprobar
          </Button>
        ) : null,
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return <EmptyState title="Configura una compañía primero" description="No hay compañías registradas todavía." />
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Solicitudes de compra</h1>
        <Button onClick={() => setModalOpen(true)}>Nueva solicitud</Button>
      </header>

      <Card>
        {requisitionsQuery.isLoading ? (
          <LoadingState label="Cargando solicitudes…" />
        ) : requisitionsQuery.isError ? (
          <ErrorState onRetry={() => requisitionsQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={requisitionsQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay solicitudes de compra."
          />
        )}
      </Card>

      <Modal open={modalOpen} title="Nueva solicitud de compra" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input label="Descripción del ítem/servicio" value={description} onChange={(e) => setDescription(e.target.value)} required />
          <Input label="Cantidad" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
          <Input label="Justificación" value={justification} onChange={(e) => setJustification(e.target.value)} />
          <Button type="submit" loading={createMutation.isPending} disabled={!description || !quantity}>
            Guardar
          </Button>
        </form>
      </Modal>
    </div>
  )
}
