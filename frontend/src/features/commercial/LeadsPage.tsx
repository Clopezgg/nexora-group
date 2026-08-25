import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, Modal, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { crmService } from '../../services/crmService'
import type { Lead } from '../../types/crm'

export function LeadsPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const [modalOpen, setModalOpen] = useState(false)
  const [name, setName] = useState('')
  const [contactName, setContactName] = useState('')
  const [email, setEmail] = useState('')
  const queryClient = useQueryClient()

  const leadsQuery = useQuery({
    queryKey: ['crm', 'leads', activeCompanyId],
    queryFn: () => crmService.listLeads(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['crm', 'leads', activeCompanyId] })
    queryClient.invalidateQueries({ queryKey: ['crm', 'customers', activeCompanyId] })
    queryClient.invalidateQueries({ queryKey: ['crm', 'opportunities', activeCompanyId] })
  }

  const createMutation = useMutation({
    mutationFn: () =>
      crmService.createLead({
        companyId: activeCompanyId as string,
        name,
        contactName: contactName || undefined,
        email: email || undefined,
      }),
    onSuccess: () => {
      invalidate()
      setModalOpen(false)
      setName('')
      setContactName('')
      setEmail('')
    },
  })

  const convertMutation = useMutation({
    mutationFn: (leadId: string) => crmService.convertLead(leadId),
    onSuccess: invalidate,
  })

  const columns: TableColumn<Lead>[] = [
    { key: 'name', header: 'Nombre / empresa', render: (row) => row.name },
    { key: 'contactName', header: 'Contacto', render: (row) => row.contactName ?? '—' },
    { key: 'source', header: 'Origen', render: (row) => row.source ?? '—' },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{row.status}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) =>
        row.status === 'CONVERTED' ? (
          <span className="nx-field__hint">Convertido a cliente</span>
        ) : (
          <Button
            variant="secondary"
            loading={convertMutation.isPending}
            onClick={() => convertMutation.mutate(row.id)}
          >
            Convertir a cliente
          </Button>
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
        <h1 className="nx-dashboard__title">Leads</h1>
        <Button onClick={() => setModalOpen(true)}>Nuevo lead</Button>
      </header>

      <Card>
        {leadsQuery.isLoading ? (
          <LoadingState label="Cargando leads…" />
        ) : leadsQuery.isError ? (
          <ErrorState onRetry={() => leadsQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={leadsQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay leads registrados."
          />
        )}
      </Card>

      <Modal open={modalOpen} title="Nuevo lead" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input label="Nombre / empresa" value={name} onChange={(e) => setName(e.target.value)} required />
          <Input label="Contacto" value={contactName} onChange={(e) => setContactName(e.target.value)} />
          <Input label="Correo" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Button type="submit" loading={createMutation.isPending} disabled={!name}>
            Guardar
          </Button>
        </form>
      </Modal>
    </div>
  )
}
