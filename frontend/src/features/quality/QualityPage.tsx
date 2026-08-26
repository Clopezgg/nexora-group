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
  Select,
  Table,
  Tabs,
  Textarea,
  type TableColumn,
} from '../../design-system'
import { useAuth } from '../auth/auth-context'
import { useCompanyUsers } from '../../hooks/useCompanyUsers'
import { RequiresActiveProject } from '../projects/RequiresActiveProject'
import { projectService } from '../../services/projectService'
import { qualityService } from '../../services/qualityService'
import type { CorrectiveAction, NonConformance, QualityInspection } from '../../types/quality'

const RESULT_TONE: Record<QualityInspection['result'], 'neutral' | 'success' | 'danger'> = {
  PENDING: 'neutral',
  PASS: 'success',
  FAIL: 'danger',
}

const NC_STATUS_TONE: Record<NonConformance['status'], 'warning' | 'success'> = {
  OPEN: 'warning',
  CLOSED: 'success',
}

const CA_STATUS_TONE: Record<CorrectiveAction['status'], 'warning' | 'success'> = {
  OPEN: 'warning',
  COMPLETED: 'success',
}

function InspectionsTab({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({
    inspectionType: '',
    inspectionDate: '',
    result: 'PENDING' as QualityInspection['result'],
    notes: '',
  })

  const inspectionsQuery = useQuery({
    queryKey: ['quality', 'inspections', projectId],
    queryFn: () => qualityService.listInspections(projectId),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      qualityService.createInspection({
        projectId,
        inspectionType: form.inspectionType,
        inspectionDate: form.inspectionDate,
        result: form.result,
        notes: form.notes || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quality', 'inspections', projectId] })
      setModalOpen(false)
      setForm({ inspectionType: '', inspectionDate: '', result: 'PENDING', notes: '' })
    },
  })

  const columns: TableColumn<QualityInspection>[] = [
    { key: 'date', header: 'Fecha', render: (row) => row.inspectionDate },
    { key: 'type', header: 'Tipo', render: (row) => row.inspectionType },
    {
      key: 'result',
      header: 'Resultado',
      render: (row) => <Badge tone={RESULT_TONE[row.result]}>{row.result}</Badge>,
    },
    { key: 'notes', header: 'Notas', render: (row) => row.notes ?? '—' },
  ]

  const inspections = inspectionsQuery.data ?? []

  return (
    <div>
      <header className="nx-page__header">
        <h2>Inspecciones de calidad</h2>
        <Button onClick={() => setModalOpen(true)}>Nueva inspección</Button>
      </header>

      <Card>
        {inspectionsQuery.isLoading ? (
          <LoadingState label="Cargando inspecciones…" />
        ) : inspectionsQuery.isError ? (
          <ErrorState onRetry={() => inspectionsQuery.refetch()} />
        ) : inspections.length === 0 ? (
          <EmptyState icon="🔍" title="Sin inspecciones" description="Registra la primera inspección de calidad de este proyecto." />
        ) : (
          <Table columns={columns} rows={inspections} getRowKey={(row) => row.id} emptyMessage="Aún no hay inspecciones." />
        )}
      </Card>

      <Modal open={modalOpen} title="Nueva inspección de calidad" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input
            label="Tipo de inspección"
            value={form.inspectionType}
            onChange={(e) => setForm({ ...form, inspectionType: e.target.value })}
            required
          />
          <Input
            label="Fecha"
            type="date"
            value={form.inspectionDate}
            onChange={(e) => setForm({ ...form, inspectionDate: e.target.value })}
            required
          />
          <Select
            label="Resultado"
            value={form.result}
            onChange={(e) => setForm({ ...form, result: e.target.value as QualityInspection['result'] })}
          >
            <option value="PENDING">Pendiente</option>
            <option value="PASS">Aprobado</option>
            <option value="FAIL">Rechazado</option>
          </Select>
          <Textarea label="Notas" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          <Button type="submit" loading={createMutation.isPending} disabled={!form.inspectionType || !form.inspectionDate}>
            Guardar
          </Button>
          {createMutation.isError ? <p className="nx-field__error">{String(createMutation.error)}</p> : null}
        </form>
      </Modal>
    </div>
  )
}

function NonConformancesTab({ projectId }: { projectId: string }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const projectQuery = useQuery({ queryKey: ['project', projectId], queryFn: () => projectService.get(projectId) })
  const { users: companyUsers } = useCompanyUsers(projectQuery.data?.companyId)
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({ description: '', responsibleUserId: user?.id ?? '', dueDate: '' })
  const [selected, setSelected] = useState<NonConformance | null>(null)

  const nonConformancesQuery = useQuery({
    queryKey: ['quality', 'non-conformances', projectId],
    queryFn: () => qualityService.listNonConformances(projectId),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['quality', 'non-conformances', projectId] })

  const createMutation = useMutation({
    mutationFn: () =>
      qualityService.createNonConformance({
        projectId,
        description: form.description,
        responsibleUserId: form.responsibleUserId,
        dueDate: form.dueDate || undefined,
      }),
    onSuccess: () => {
      invalidate()
      setModalOpen(false)
      setForm({ description: '', responsibleUserId: user?.id ?? '', dueDate: '' })
    },
  })

  const columns: TableColumn<NonConformance>[] = [
    { key: 'description', header: 'Descripción', render: (row) => row.description },
    { key: 'dueDate', header: 'Fecha límite', render: (row) => row.dueDate ?? '—' },
    {
      key: 'status',
      header: 'Estado',
      render: (row) => <Badge tone={NC_STATUS_TONE[row.status]}>{row.status}</Badge>,
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <Button variant="secondary" onClick={() => setSelected(row)}>
          Ver acciones correctivas
        </Button>
      ),
    },
  ]

  const nonConformances = nonConformancesQuery.data ?? []

  return (
    <div>
      <header className="nx-page__header">
        <h2>No conformidades</h2>
        <Button onClick={() => setModalOpen(true)}>Nueva no conformidad</Button>
      </header>

      <Card>
        {nonConformancesQuery.isLoading ? (
          <LoadingState label="Cargando no conformidades…" />
        ) : nonConformancesQuery.isError ? (
          <ErrorState onRetry={() => nonConformancesQuery.refetch()} />
        ) : nonConformances.length === 0 ? (
          <EmptyState icon="⚠️" title="Sin no conformidades" description="Registra la primera no conformidad de este proyecto." />
        ) : (
          <Table columns={columns} rows={nonConformances} getRowKey={(row) => row.id} emptyMessage="Aún no hay no conformidades." />
        )}
      </Card>

      <Modal open={modalOpen} title="Nueva no conformidad" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Textarea
            label="Descripción"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            required
          />
          <Select
            label="Usuario responsable"
            value={form.responsibleUserId}
            onChange={(e) => setForm({ ...form, responsibleUserId: e.target.value })}
            required
          >
            {companyUsers.map((u) => (
              <option key={u.id} value={u.id}>
                {u.fullName} ({u.email})
              </option>
            ))}
          </Select>
          <Input
            label="Fecha límite"
            type="date"
            value={form.dueDate}
            onChange={(e) => setForm({ ...form, dueDate: e.target.value })}
          />
          <Button type="submit" loading={createMutation.isPending} disabled={!form.description || !form.responsibleUserId}>
            Guardar
          </Button>
          {createMutation.isError ? <p className="nx-field__error">{String(createMutation.error)}</p> : null}
        </form>
      </Modal>

      <CorrectiveActionsModal nonConformance={selected} onClose={() => setSelected(null)} onChanged={invalidate} />
    </div>
  )
}

function CorrectiveActionsModal({
  nonConformance,
  onClose,
  onChanged,
}: {
  nonConformance: NonConformance | null
  onClose: () => void
  onChanged: () => void
}) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const projectQuery = useQuery({
    queryKey: ['project', nonConformance?.projectId],
    queryFn: () => projectService.get(nonConformance!.projectId),
    enabled: Boolean(nonConformance),
  })
  const { users: companyUsers } = useCompanyUsers(projectQuery.data?.companyId)
  const [form, setForm] = useState({ description: '', responsibleUserId: user?.id ?? '', dueDate: '' })

  const actionsQuery = useQuery({
    queryKey: ['quality', 'corrective-actions', nonConformance?.id],
    queryFn: () => qualityService.listCorrectiveActions(nonConformance!.id),
    enabled: Boolean(nonConformance),
  })

  const invalidateActions = () =>
    queryClient.invalidateQueries({ queryKey: ['quality', 'corrective-actions', nonConformance?.id] })

  const createActionMutation = useMutation({
    mutationFn: () => {
      if (!nonConformance) throw new Error('No hay no conformidad seleccionada')
      return qualityService.createCorrectiveAction(nonConformance.id, {
        description: form.description,
        responsibleUserId: form.responsibleUserId,
        dueDate: form.dueDate,
      })
    },
    onSuccess: () => {
      invalidateActions()
      setForm({ description: '', responsibleUserId: user?.id ?? '', dueDate: '' })
    },
  })

  const completeActionMutation = useMutation({
    mutationFn: (correctiveActionId: string) => qualityService.completeCorrectiveAction(correctiveActionId),
    onSuccess: invalidateActions,
  })

  const closeMutation = useMutation({
    mutationFn: () => {
      if (!nonConformance) throw new Error('No hay no conformidad seleccionada')
      return qualityService.closeNonConformance(nonConformance.id)
    },
    onSuccess: () => {
      invalidateActions()
      onChanged()
    },
  })

  if (!nonConformance) return null

  const actions = actionsQuery.data ?? []

  return (
    <Modal open={Boolean(nonConformance)} title={`Acciones correctivas — ${nonConformance.description}`} onClose={onClose}>
      <p>
        Estado: <Badge tone={NC_STATUS_TONE[nonConformance.status]}>{nonConformance.status}</Badge>
      </p>

      {actionsQuery.isLoading ? (
        <LoadingState label="Cargando acciones correctivas…" />
      ) : actions.length === 0 ? (
        <p>Sin acciones correctivas registradas todavía. No se puede cerrar la no conformidad sin al menos una.</p>
      ) : (
        <ul>
          {actions.map((action) => (
            <li key={action.id}>
              {action.description} — <Badge tone={CA_STATUS_TONE[action.status]}>{action.status}</Badge>
              {action.status === 'OPEN' && nonConformance.status === 'OPEN' ? (
                <Button
                  variant="ghost"
                  loading={completeActionMutation.isPending}
                  onClick={() => completeActionMutation.mutate(action.id)}
                >
                  Completar
                </Button>
              ) : null}
            </li>
          ))}
        </ul>
      )}

      {nonConformance.status === 'OPEN' ? (
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createActionMutation.mutate()
          }}
        >
          <Textarea
            label="Descripción de la acción correctiva"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            required
          />
          <Select
            label="Usuario responsable"
            value={form.responsibleUserId}
            onChange={(e) => setForm({ ...form, responsibleUserId: e.target.value })}
            required
          >
            {companyUsers.map((u) => (
              <option key={u.id} value={u.id}>
                {u.fullName} ({u.email})
              </option>
            ))}
          </Select>
          <Input
            label="Fecha límite"
            type="date"
            value={form.dueDate}
            onChange={(e) => setForm({ ...form, dueDate: e.target.value })}
            required
          />
          <Button
            type="submit"
            variant="secondary"
            loading={createActionMutation.isPending}
            disabled={!form.description || !form.responsibleUserId || !form.dueDate}
          >
            Agregar acción correctiva
          </Button>
          {createActionMutation.isError ? (
            <p className="nx-field__error">{String(createActionMutation.error)}</p>
          ) : null}
        </form>
      ) : null}

      {nonConformance.status === 'OPEN' ? (
        <div style={{ marginTop: 16 }}>
          <Button loading={closeMutation.isPending} onClick={() => closeMutation.mutate()}>
            Cerrar no conformidad
          </Button>
          {closeMutation.isError ? <p className="nx-field__error">{String(closeMutation.error)}</p> : null}
        </div>
      ) : null}
    </Modal>
  )
}

function QualityTabs({ projectId }: { projectId: string }) {
  return (
    <Tabs
      items={[
        { key: 'inspections', label: 'Inspecciones', content: <InspectionsTab projectId={projectId} /> },
        { key: 'non-conformances', label: 'No conformidades', content: <NonConformancesTab projectId={projectId} /> },
      ]}
    />
  )
}

export function QualityPage() {
  return (
    <div>
      <RequiresActiveProject>{(projectId) => <QualityTabs projectId={projectId} />}</RequiresActiveProject>
    </div>
  )
}
