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
  SupplierSelector,
  Table,
  Textarea,
} from '../../design-system'
import type { TableColumn } from '../../design-system'
import { procurementService } from '../../services/procurementService'
import { projectService } from '../../services/projectService'
import { submittalService } from '../../services/submittalService'
import type { Submittal } from '../../types/submittal'
import { RequiresActiveProject } from '../projects/RequiresActiveProject'

const STATUS_TONE: Record<Submittal['status'], 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = {
  SUBMITTED: 'neutral',
  UNDER_REVIEW: 'warning',
  APPROVED: 'success',
  REJECTED: 'danger',
}

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10)
}

function SubmittalsList({ projectId, companyId }: { projectId: string; companyId: string }) {
  const queryClient = useQueryClient()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [supplierId, setSupplierId] = useState<string | null>(null)
  const [selected, setSelected] = useState<Submittal | null>(null)
  const [reviewText, setReviewText] = useState('')

  const submittalsQuery = useQuery({
    queryKey: ['submittals', projectId],
    queryFn: () => submittalService.list(companyId, projectId),
  })
  const suppliersQuery = useQuery({
    queryKey: ['procurement', 'suppliers', companyId],
    queryFn: () => procurementService.listSuppliers(companyId),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['submittals', projectId] })

  const createSubmittal = useMutation({
    mutationFn: () =>
      submittalService.create({
        companyId,
        projectId,
        title,
        description: description || undefined,
        supplierId: supplierId ?? undefined,
        submittedAt: todayIsoDate(),
      }),
    onSuccess: () => {
      setTitle('')
      setDescription('')
      setSupplierId(null)
      invalidate()
    },
  })

  const recordResponse = useMutation({
    mutationFn: () => {
      if (!selected) throw new Error('No hay submittal seleccionado')
      return submittalService.recordResponse(selected.id, reviewText)
    },
    onSuccess: (updated) => {
      setReviewText('')
      setSelected(updated)
      invalidate()
    },
  })

  const decide = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: 'APPROVED' | 'REJECTED' }) =>
      submittalService.decide(id, decision),
    onSuccess: () => {
      setSelected(null)
      invalidate()
    },
  })

  if (submittalsQuery.isLoading) return <LoadingState label="Cargando submittals…" />
  if (submittalsQuery.isError) {
    return <ErrorState description="No se pudieron cargar los submittals." onRetry={() => submittalsQuery.refetch()} />
  }

  const submittals = submittalsQuery.data ?? []
  const supplierOptions = (suppliersQuery.data ?? []).map((s) => ({ id: s.id, label: s.legalName }))

  const columns: TableColumn<Submittal>[] = [
    { key: 'number', header: 'Número', render: (row) => `${row.number} (rev. ${row.revision})` },
    { key: 'title', header: 'Título', render: (row) => row.title },
    { key: 'status', header: 'Estado', render: (row) => <Badge tone={STATUS_TONE[row.status]}>{row.status}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) =>
        row.status === 'APPROVED' || row.status === 'REJECTED' ? null : (
          <Button variant="secondary" onClick={() => setSelected(row)}>
            Revisar
          </Button>
        ),
    },
  ]

  return (
    <div>
      <Card title="Nuevo Submittal">
        <Input label="Título" value={title} onChange={(event) => setTitle(event.target.value)} required />
        <Textarea
          label="Descripción"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
        />
        <SupplierSelector options={supplierOptions} value={supplierId} onChange={setSupplierId} />
        <Button
          disabled={!title || createSubmittal.isPending}
          loading={createSubmittal.isPending}
          onClick={() => createSubmittal.mutate()}
        >
          Crear submittal
        </Button>
        {createSubmittal.isError ? <p className="nx-field__error">{String(createSubmittal.error)}</p> : null}
      </Card>

      {submittals.length === 0 ? (
        <EmptyState icon="clipboard" title="Sin submittals registrados" description="Todavía no se ha enviado ningún submittal en este proyecto." />
      ) : (
        <Table columns={columns} rows={submittals} getRowKey={(row) => row.id} />
      )}

      {selected ? (
        <Card title={`Revisar ${selected.number}`}>
          <p>{selected.title}</p>
          <Textarea
            label="Respuesta del revisor"
            value={reviewText}
            onChange={(event) => setReviewText(event.target.value)}
            placeholder={selected.reviewerResponse ?? 'Registra la respuesta antes de aprobar/rechazar'}
          />
          <Button
            variant="secondary"
            disabled={!reviewText || recordResponse.isPending}
            loading={recordResponse.isPending}
            onClick={() => recordResponse.mutate()}
          >
            Guardar respuesta
          </Button>

          <div className="nx-page__header">
            <Button
              disabled={!selected.reviewerResponse || decide.isPending}
              loading={decide.isPending}
              onClick={() => decide.mutate({ id: selected.id, decision: 'APPROVED' })}
            >
              Aprobar
            </Button>
            <Button
              variant="secondary"
              disabled={!selected.reviewerResponse || decide.isPending}
              loading={decide.isPending}
              onClick={() => decide.mutate({ id: selected.id, decision: 'REJECTED' })}
            >
              Rechazar
            </Button>
            <Button variant="secondary" onClick={() => setSelected(null)}>
              Cerrar
            </Button>
          </div>
          {!selected.reviewerResponse ? (
            <p className="nx-field__hint">Registra la respuesta del revisor antes de aprobar o rechazar.</p>
          ) : null}
          {recordResponse.isError ? <p className="nx-field__error">{String(recordResponse.error)}</p> : null}
          {decide.isError ? <p className="nx-field__error">{String(decide.error)}</p> : null}
        </Card>
      ) : null}
    </div>
  )
}

function SubmittalsForProject({ projectId }: { projectId: string }) {
  const projectQuery = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectService.get(projectId),
  })

  if (projectQuery.isLoading) return <LoadingState label="Cargando proyecto…" />
  if (projectQuery.isError || !projectQuery.data) {
    return <ErrorState description="No se pudo cargar el proyecto activo." onRetry={() => projectQuery.refetch()} />
  }

  return <SubmittalsList projectId={projectId} companyId={projectQuery.data.companyId} />
}

export function SubmittalsPage() {
  return (
    <div>
      <h1 className="nx-dashboard__title">Submittals</h1>
      <RequiresActiveProject>{(projectId) => <SubmittalsForProject projectId={projectId} />}</RequiresActiveProject>
    </div>
  )
}
