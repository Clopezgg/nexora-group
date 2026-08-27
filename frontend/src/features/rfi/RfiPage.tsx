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
  Table,
  Textarea,
} from '../../design-system'
import type { TableColumn } from '../../design-system'
import { projectService } from '../../services/projectService'
import { rfiService } from '../../services/rfiService'
import type { Rfi } from '../../types/rfi'
import { RequiresActiveProject } from '../projects/RequiresActiveProject'

const STATUS_TONE: Record<Rfi['status'], 'neutral' | 'success' | 'warning' | 'danger' | 'info'> = {
  OPEN: 'warning',
  ANSWERED: 'info',
  CLOSED: 'success',
}

function RfiList({ projectId, companyId }: { projectId: string; companyId: string }) {
  const queryClient = useQueryClient()
  const [subject, setSubject] = useState('')
  const [question, setQuestion] = useState('')
  const [responsible, setResponsible] = useState('')
  const [selectedRfi, setSelectedRfi] = useState<Rfi | null>(null)
  const [responseText, setResponseText] = useState('')

  const rfisQuery = useQuery({
    queryKey: ['rfis', projectId],
    queryFn: () => rfiService.list(companyId, projectId),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['rfis', projectId] })

  const createRfi = useMutation({
    mutationFn: () => rfiService.create({ companyId, projectId, subject, question, responsible: responsible || undefined }),
    onSuccess: () => {
      setSubject('')
      setQuestion('')
      setResponsible('')
      invalidate()
    },
  })

  const respondRfi = useMutation({
    mutationFn: () => {
      if (!selectedRfi) throw new Error('No hay RFI seleccionado')
      return rfiService.respond(selectedRfi.id, responseText)
    },
    onSuccess: () => {
      setResponseText('')
      setSelectedRfi(null)
      invalidate()
    },
  })

  const closeRfi = useMutation({
    mutationFn: (id: string) => rfiService.close(id),
    onSuccess: invalidate,
  })

  if (rfisQuery.isLoading) return <LoadingState label="Cargando RFI…" />
  if (rfisQuery.isError) {
    return <ErrorState description="No se pudieron cargar los RFI." onRetry={() => rfisQuery.refetch()} />
  }

  const rfis = rfisQuery.data ?? []

  const columns: TableColumn<Rfi>[] = [
    { key: 'number', header: 'Número', render: (row) => row.number },
    { key: 'subject', header: 'Asunto', render: (row) => row.subject },
    { key: 'responsible', header: 'Responsable', render: (row) => row.responsible ?? '—' },
    { key: 'status', header: 'Estado', render: (row) => <Badge tone={STATUS_TONE[row.status]}>{row.status}</Badge> },
    {
      key: 'actions',
      header: 'Acciones',
      render: (row) => (
        <>
          {row.status === 'OPEN' ? (
            <Button variant="secondary" onClick={() => setSelectedRfi(row)}>
              Responder
            </Button>
          ) : null}
          {row.status === 'ANSWERED' ? (
            <Button variant="secondary" loading={closeRfi.isPending} onClick={() => closeRfi.mutate(row.id)}>
              Cerrar
            </Button>
          ) : null}
        </>
      ),
    },
  ]

  return (
    <div>
      <Card title="Nuevo RFI">
        <Input label="Asunto" value={subject} onChange={(event) => setSubject(event.target.value)} required />
        <Textarea label="Pregunta" value={question} onChange={(event) => setQuestion(event.target.value)} required />
        <Input
          label="Responsable"
          value={responsible}
          onChange={(event) => setResponsible(event.target.value)}
        />
        <Button
          disabled={!subject || !question || createRfi.isPending}
          loading={createRfi.isPending}
          onClick={() => createRfi.mutate()}
        >
          Crear RFI
        </Button>
        {createRfi.isError ? <p className="nx-field__error">{String(createRfi.error)}</p> : null}
      </Card>

      {rfis.length === 0 ? (
        <EmptyState icon="file" title="Sin RFI registrados" description="Todavía no se ha levantado ningún RFI en este proyecto." />
      ) : (
        <Table columns={columns} rows={rfis} getRowKey={(row) => row.id} />
      )}

      {selectedRfi ? (
        <Card title={`Responder ${selectedRfi.number}`}>
          <p>{selectedRfi.question}</p>
          <Textarea
            label="Respuesta"
            value={responseText}
            onChange={(event) => setResponseText(event.target.value)}
            required
          />
          <Button
            disabled={!responseText || respondRfi.isPending}
            loading={respondRfi.isPending}
            onClick={() => respondRfi.mutate()}
          >
            Guardar respuesta
          </Button>
          <Button variant="secondary" onClick={() => setSelectedRfi(null)}>
            Cancelar
          </Button>
          {respondRfi.isError ? <p className="nx-field__error">{String(respondRfi.error)}</p> : null}
        </Card>
      ) : null}
    </div>
  )
}

function RfiForProject({ projectId }: { projectId: string }) {
  const projectQuery = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectService.get(projectId),
  })

  if (projectQuery.isLoading) return <LoadingState label="Cargando proyecto…" />
  if (projectQuery.isError || !projectQuery.data) {
    return <ErrorState description="No se pudo cargar el proyecto activo." onRetry={() => projectQuery.refetch()} />
  }

  return <RfiList projectId={projectId} companyId={projectQuery.data.companyId} />
}

export function RfiPage() {
  return (
    <div>
      <h1 className="nx-dashboard__title">RFI (Request For Information)</h1>
      <RequiresActiveProject>{(projectId) => <RfiForProject projectId={projectId} />}</RequiresActiveProject>
    </div>
  )
}
