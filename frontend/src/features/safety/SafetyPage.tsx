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
import { safetyService } from '../../services/safetyService'
import type { SafetyIncident, SafetyObservation, SafetySeverity } from '../../types/safety'

const SEVERITY_TONE: Record<SafetySeverity, 'neutral' | 'warning' | 'danger'> = {
  LOW: 'neutral',
  MEDIUM: 'warning',
  HIGH: 'danger',
  CRITICAL: 'danger',
}

const STATUS_TONE: Record<'OPEN' | 'CLOSED', 'warning' | 'success'> = {
  OPEN: 'warning',
  CLOSED: 'success',
}

const SEVERITIES_REQUIRING_RESPONSIBLE: SafetySeverity[] = ['HIGH', 'CRITICAL']

function ObservationsTab({ projectId }: { projectId: string }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const projectQuery = useQuery({ queryKey: ['project', projectId], queryFn: () => projectService.get(projectId) })
  const { users: companyUsers } = useCompanyUsers(projectQuery.data?.companyId)
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({
    observationDate: '',
    category: '',
    description: '',
    severity: 'LOW' as SafetySeverity,
    responsibleUserId: '',
  })

  const observationsQuery = useQuery({
    queryKey: ['safety', 'observations', projectId],
    queryFn: () => safetyService.listObservations(projectId),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['safety', 'observations', projectId] })

  const requiresResponsible = SEVERITIES_REQUIRING_RESPONSIBLE.includes(form.severity)

  const createMutation = useMutation({
    mutationFn: () =>
      safetyService.createObservation({
        projectId,
        observationDate: form.observationDate,
        category: form.category,
        description: form.description,
        severity: form.severity,
        responsibleUserId: form.responsibleUserId || undefined,
      }),
    onSuccess: () => {
      invalidate()
      setModalOpen(false)
      setForm({ observationDate: '', category: '', description: '', severity: 'LOW', responsibleUserId: '' })
    },
  })

  const closeMutation = useMutation({
    mutationFn: (observationId: string) => safetyService.closeObservation(observationId),
    onSuccess: invalidate,
  })

  const columns: TableColumn<SafetyObservation>[] = [
    { key: 'date', header: 'Fecha', render: (row) => row.observationDate },
    { key: 'category', header: 'Categoría', render: (row) => row.category },
    { key: 'description', header: 'Descripción', render: (row) => row.description },
    {
      key: 'severity',
      header: 'Severidad',
      render: (row) => <Badge tone={SEVERITY_TONE[row.severity]}>{row.severity}</Badge>,
    },
    { key: 'responsible', header: 'Responsable', render: (row) => row.responsibleUserId?.slice(0, 8) ?? '—' },
    {
      key: 'status',
      header: 'Estado',
      render: (row) => <Badge tone={STATUS_TONE[row.status]}>{row.status}</Badge>,
    },
    {
      key: 'actions',
      header: '',
      render: (row) =>
        row.status === 'OPEN' ? (
          <Button variant="secondary" loading={closeMutation.isPending} onClick={() => closeMutation.mutate(row.id)}>
            Cerrar
          </Button>
        ) : null,
    },
  ]

  const observations = observationsQuery.data ?? []

  return (
    <div>
      <header className="nx-page__header">
        <h2>Observaciones de seguridad</h2>
        <Button
          onClick={() => {
            setForm({ ...form, responsibleUserId: user?.id ?? '' })
            setModalOpen(true)
          }}
        >
          Nueva observación
        </Button>
      </header>

      <Card>
        {observationsQuery.isLoading ? (
          <LoadingState label="Cargando observaciones…" />
        ) : observationsQuery.isError ? (
          <ErrorState onRetry={() => observationsQuery.refetch()} />
        ) : observations.length === 0 ? (
          <EmptyState icon="🦺" title="Sin observaciones" description="Registra la primera observación de seguridad de este proyecto." />
        ) : (
          <Table columns={columns} rows={observations} getRowKey={(row) => row.id} emptyMessage="Aún no hay observaciones." />
        )}
      </Card>

      <Modal open={modalOpen} title="Nueva observación de seguridad" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input
            label="Fecha"
            type="date"
            value={form.observationDate}
            onChange={(e) => setForm({ ...form, observationDate: e.target.value })}
            required
          />
          <Input
            label="Categoría"
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            required
          />
          <Textarea
            label="Descripción"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            required
          />
          <Select
            label="Severidad"
            value={form.severity}
            onChange={(e) => setForm({ ...form, severity: e.target.value as SafetySeverity })}
          >
            <option value="LOW">Baja</option>
            <option value="MEDIUM">Media</option>
            <option value="HIGH">Alta</option>
            <option value="CRITICAL">Crítica</option>
          </Select>
          <Select
            label={
              requiresResponsible
                ? 'Usuario responsable — obligatorio para severidad Alta o Crítica'
                : 'Usuario responsable — opcional para esta severidad'
            }
            value={form.responsibleUserId}
            onChange={(e) => setForm({ ...form, responsibleUserId: e.target.value })}
            required={requiresResponsible}
          >
            {requiresResponsible ? null : <option value="">— sin asignar —</option>}
            {companyUsers.map((u) => (
              <option key={u.id} value={u.id}>
                {u.fullName} ({u.email})
              </option>
            ))}
          </Select>
          <Button
            type="submit"
            loading={createMutation.isPending}
            disabled={!form.observationDate || !form.category || !form.description || (requiresResponsible && !form.responsibleUserId)}
          >
            Guardar
          </Button>
          {createMutation.isError ? <p className="nx-field__error">{String(createMutation.error)}</p> : null}
        </form>
      </Modal>
    </div>
  )
}

function IncidentsTab({ projectId }: { projectId: string }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const projectQuery = useQuery({ queryKey: ['project', projectId], queryFn: () => projectService.get(projectId) })
  const { users: companyUsers } = useCompanyUsers(projectQuery.data?.companyId)
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState({
    incidentDate: '',
    description: '',
    severity: 'LOW' as SafetySeverity,
    responsibleUserId: '',
  })

  const incidentsQuery = useQuery({
    queryKey: ['safety', 'incidents', projectId],
    queryFn: () => safetyService.listIncidents(projectId),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['safety', 'incidents', projectId] })

  const requiresResponsible = SEVERITIES_REQUIRING_RESPONSIBLE.includes(form.severity)

  const createMutation = useMutation({
    mutationFn: () =>
      safetyService.createIncident({
        projectId,
        incidentDate: form.incidentDate,
        description: form.description,
        severity: form.severity,
        responsibleUserId: form.responsibleUserId || undefined,
      }),
    onSuccess: () => {
      invalidate()
      setModalOpen(false)
      setForm({ incidentDate: '', description: '', severity: 'LOW', responsibleUserId: '' })
    },
  })

  const closeMutation = useMutation({
    mutationFn: (incidentId: string) => safetyService.closeIncident(incidentId),
    onSuccess: invalidate,
  })

  const columns: TableColumn<SafetyIncident>[] = [
    { key: 'date', header: 'Fecha', render: (row) => row.incidentDate },
    { key: 'description', header: 'Descripción', render: (row) => row.description },
    {
      key: 'severity',
      header: 'Severidad',
      render: (row) => <Badge tone={SEVERITY_TONE[row.severity]}>{row.severity}</Badge>,
    },
    { key: 'responsible', header: 'Responsable', render: (row) => row.responsibleUserId?.slice(0, 8) ?? '—' },
    {
      key: 'status',
      header: 'Estado',
      render: (row) => <Badge tone={STATUS_TONE[row.status]}>{row.status}</Badge>,
    },
    {
      key: 'actions',
      header: '',
      render: (row) =>
        row.status === 'OPEN' ? (
          <Button variant="secondary" loading={closeMutation.isPending} onClick={() => closeMutation.mutate(row.id)}>
            Cerrar
          </Button>
        ) : null,
    },
  ]

  const incidents = incidentsQuery.data ?? []

  return (
    <div>
      <header className="nx-page__header">
        <h2>Incidentes de seguridad</h2>
        <Button
          onClick={() => {
            setForm({ ...form, responsibleUserId: user?.id ?? '' })
            setModalOpen(true)
          }}
        >
          Nuevo incidente
        </Button>
      </header>

      <Card>
        {incidentsQuery.isLoading ? (
          <LoadingState label="Cargando incidentes…" />
        ) : incidentsQuery.isError ? (
          <ErrorState onRetry={() => incidentsQuery.refetch()} />
        ) : incidents.length === 0 ? (
          <EmptyState icon="🚨" title="Sin incidentes" description="Registra el primer incidente de seguridad de este proyecto." />
        ) : (
          <Table columns={columns} rows={incidents} getRowKey={(row) => row.id} emptyMessage="Aún no hay incidentes." />
        )}
      </Card>

      <Modal open={modalOpen} title="Nuevo incidente de seguridad" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input
            label="Fecha"
            type="date"
            value={form.incidentDate}
            onChange={(e) => setForm({ ...form, incidentDate: e.target.value })}
            required
          />
          <Textarea
            label="Descripción"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            required
          />
          <Select
            label="Severidad"
            value={form.severity}
            onChange={(e) => setForm({ ...form, severity: e.target.value as SafetySeverity })}
          >
            <option value="LOW">Baja</option>
            <option value="MEDIUM">Media</option>
            <option value="HIGH">Alta</option>
            <option value="CRITICAL">Crítica</option>
          </Select>
          <Select
            label={
              requiresResponsible
                ? 'Usuario responsable — obligatorio para severidad Alta o Crítica'
                : 'Usuario responsable — opcional para esta severidad'
            }
            value={form.responsibleUserId}
            onChange={(e) => setForm({ ...form, responsibleUserId: e.target.value })}
            required={requiresResponsible}
          >
            {requiresResponsible ? null : <option value="">— sin asignar —</option>}
            {companyUsers.map((u) => (
              <option key={u.id} value={u.id}>
                {u.fullName} ({u.email})
              </option>
            ))}
          </Select>
          <Button
            type="submit"
            loading={createMutation.isPending}
            disabled={!form.incidentDate || !form.description || (requiresResponsible && !form.responsibleUserId)}
          >
            Guardar
          </Button>
          {createMutation.isError ? <p className="nx-field__error">{String(createMutation.error)}</p> : null}
        </form>
      </Modal>
    </div>
  )
}

function SafetyTabs({ projectId }: { projectId: string }) {
  return (
    <Tabs
      items={[
        { key: 'observations', label: 'Observaciones', content: <ObservationsTab projectId={projectId} /> },
        { key: 'incidents', label: 'Incidentes', content: <IncidentsTab projectId={projectId} /> },
      ]}
    />
  )
}

export function SafetyPage() {
  return (
    <div>
      <RequiresActiveProject>{(projectId) => <SafetyTabs projectId={projectId} />}</RequiresActiveProject>
    </div>
  )
}
