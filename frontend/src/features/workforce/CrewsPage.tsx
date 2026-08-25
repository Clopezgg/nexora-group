import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
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
import { useActiveContext } from '../context/useActiveContext'
import { workforceService } from '../../services/workforceService'
import type { Crew } from '../../types/workforce'

/** NXR-REQ-0074. `/recursos/cuadrillas` ya existía como entrada reservada
 * ("Cuadrillas") en navigation.ts -- no se inventó una ruta nueva. Alcance
 * mínimo, mismo criterio que WorkersPage: agrupar Worker por nombre,
 * opcionalmente atribuidos al proyecto activo (ActiveUIContext, nunca
 * OperationScope -- CLAUDE.md §7), sin scheduling ni rotación de
 * membresía por fecha. */
export function CrewsPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const { context } = useActiveContext()
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [membersCrewId, setMembersCrewId] = useState<string | null>(null)
  const [form, setForm] = useState({ name: '', attributeToActiveProject: false })

  const crewsQuery = useQuery({
    queryKey: ['workforce', 'crews', activeCompanyId],
    queryFn: () => workforceService.listCrews(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      workforceService.createCrew({
        companyId: activeCompanyId as string,
        name: form.name,
        projectId:
          form.attributeToActiveProject && context.activeProjectId
            ? context.activeProjectId
            : undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workforce', 'crews', activeCompanyId] })
      setCreateOpen(false)
      setForm({ name: '', attributeToActiveProject: false })
    },
  })

  const columns: TableColumn<Crew>[] = [
    { key: 'name', header: 'Nombre', render: (row) => row.name },
    {
      key: 'projectId',
      header: 'Proyecto',
      render: (row) => (row.projectId ? row.projectId : 'General (sin proyecto)'),
    },
    {
      key: 'status',
      header: 'Estado',
      render: (row) => (
        <Badge tone={row.status === 'ACTIVE' ? 'success' : 'neutral'}>{row.status}</Badge>
      ),
    },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <Button variant="ghost" onClick={() => setMembersCrewId(row.id)}>
          Miembros
        </Button>
      ),
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="👷"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Cuadrillas</h1>
        <Button onClick={() => setCreateOpen(true)}>Nueva cuadrilla</Button>
      </header>

      <Card>
        {crewsQuery.isLoading ? (
          <LoadingState label="Cargando cuadrillas…" />
        ) : crewsQuery.isError ? (
          <ErrorState onRetry={() => crewsQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={crewsQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay cuadrillas registradas."
          />
        )}
      </Card>

      <Modal open={createOpen} title="Nueva cuadrilla" onClose={() => setCreateOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input
            name="crewName"
            label="Nombre"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            required
          />
          {context.activeProjectId ? (
            <label className="nx-field">
              <input
                type="checkbox"
                checked={form.attributeToActiveProject}
                onChange={(e) => setForm({ ...form, attributeToActiveProject: e.target.checked })}
              />
              <span className="nx-field__label">
                Asignar a {context.activeProjectName ?? 'el proyecto activo'}
              </span>
            </label>
          ) : null}
          <Button type="submit" loading={createMutation.isPending} disabled={!form.name}>
            Guardar
          </Button>
          {createMutation.isError ? (
            <p className="nx-field__error">{String(createMutation.error)}</p>
          ) : null}
        </form>
      </Modal>

      {membersCrewId ? (
        <CrewMembersModal crewId={membersCrewId} companyId={activeCompanyId} onClose={() => setMembersCrewId(null)} />
      ) : null}
    </div>
  )
}

function CrewMembersModal({
  crewId,
  companyId,
  onClose,
}: {
  crewId: string
  companyId: string
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [selectedWorkerId, setSelectedWorkerId] = useState('')

  const crewQuery = useQuery({
    queryKey: ['workforce', 'crews', crewId],
    queryFn: () => workforceService.getCrew(crewId),
  })
  const workersQuery = useQuery({
    queryKey: ['workforce', 'workers', companyId],
    queryFn: () => workforceService.listWorkers(companyId),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['workforce', 'crews', crewId] })

  const addMutation = useMutation({
    mutationFn: () => workforceService.addCrewMember(crewId, selectedWorkerId),
    onSuccess: () => {
      invalidate()
      setSelectedWorkerId('')
    },
  })
  const removeMutation = useMutation({
    mutationFn: (workerId: string) => workforceService.removeCrewMember(crewId, workerId),
    onSuccess: () => invalidate(),
  })

  const members = crewQuery.data?.members ?? []
  const memberIds = new Set(members.map((m) => m.id))
  const availableWorkers = (workersQuery.data ?? []).filter((w) => !memberIds.has(w.id))

  return (
    <Modal open title={`Miembros de ${crewQuery.data?.name ?? '…'}`} onClose={onClose}>
      {crewQuery.isLoading ? (
        <LoadingState label="Cargando miembros…" />
      ) : (
        <>
          <ul>
            {members.map((member) => (
              <li key={member.id} className="nx-field">
                <span>{member.fullName}</span>
                <Button
                  variant="ghost"
                  loading={removeMutation.isPending}
                  onClick={() => removeMutation.mutate(member.id)}
                >
                  Quitar
                </Button>
              </li>
            ))}
          </ul>
          {members.length === 0 ? <p className="nx-field__label">Esta cuadrilla no tiene miembros todavía.</p> : null}

          <form
            onSubmit={(event) => {
              event.preventDefault()
              addMutation.mutate()
            }}
          >
            <label className="nx-field">
              <span className="nx-field__label">Agregar trabajador</span>
              <select
                className="nx-input"
                value={selectedWorkerId}
                onChange={(e) => setSelectedWorkerId(e.target.value)}
                required
              >
                <option value="" disabled>
                  Selecciona un trabajador
                </option>
                {availableWorkers.map((worker) => (
                  <option key={worker.id} value={worker.id}>
                    {worker.fullName}
                  </option>
                ))}
              </select>
            </label>
            <Button type="submit" loading={addMutation.isPending} disabled={!selectedWorkerId}>
              Agregar
            </Button>
          </form>
        </>
      )}
    </Modal>
  )
}
