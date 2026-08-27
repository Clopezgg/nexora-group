import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  Input,
  LoadingState,
  Modal,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { workforceService } from '../../services/workforceService'
import type { Worker } from '../../types/workforce'

export function WorkersPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({ fullName: '', roleTitle: '', standardHourlyRate: '' })

  const workersQuery = useQuery({
    queryKey: ['workforce', 'workers', activeCompanyId],
    queryFn: () => workforceService.listWorkers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      workforceService.createWorker({
        companyId: activeCompanyId as string,
        fullName: form.fullName,
        roleTitle: form.roleTitle || undefined,
        standardHourlyRate: form.standardHourlyRate,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workforce', 'workers', activeCompanyId] })
      setModalOpen(false)
      setForm({ fullName: '', roleTitle: '', standardHourlyRate: '' })
    },
  })

  const columns: TableColumn<Worker>[] = [
    { key: 'fullName', header: 'Nombre', render: (row) => row.fullName },
    { key: 'roleTitle', header: 'Puesto', render: (row) => row.roleTitle ?? '—' },
    {
      key: 'standardHourlyRate',
      header: 'Tarifa estándar / hora',
      render: (row) => row.standardHourlyRate,
    },
    {
      key: 'active',
      header: 'Estado',
      render: (row) => <Badge tone={row.active ? 'success' : 'neutral'}>{row.active ? 'Activo' : 'Inactivo'}</Badge>,
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="users"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Personal</h1>
        <Button onClick={() => setModalOpen(true)}>Nuevo trabajador</Button>
      </header>

      <Card>
        {workersQuery.isLoading ? (
          <LoadingState label="Cargando trabajadores…" />
        ) : workersQuery.isError ? (
          <ErrorState onRetry={() => workersQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={workersQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay trabajadores registrados."
          />
        )}
      </Card>

      <Modal open={modalOpen} title="Nuevo trabajador" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input
            label="Nombre completo"
            value={form.fullName}
            onChange={(e) => setForm({ ...form, fullName: e.target.value })}
            required
          />
          <Input
            label="Puesto"
            value={form.roleTitle}
            onChange={(e) => setForm({ ...form, roleTitle: e.target.value })}
          />
          <Input
            label="Tarifa estándar / hora"
            value={form.standardHourlyRate}
            onChange={(e) => setForm({ ...form, standardHourlyRate: e.target.value })}
            required
          />
          <Button type="submit" loading={createMutation.isPending}>
            Guardar
          </Button>
          {createMutation.isError ? (
            <p className="nx-field__error">{String(createMutation.error)}</p>
          ) : null}
        </form>
      </Modal>
    </div>
  )
}
