import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Card, EmptyState, ErrorState, Input, LoadingState, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { projectService } from '../../services/projectService'
import type { ProgressRecord } from '../../types/project'
import { RequiresActiveProject } from './RequiresActiveProject'

function ProgressList({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient()
  const [recordDate, setRecordDate] = useState('')
  const [plannedPercent, setPlannedPercent] = useState('')
  const [actualPercent, setActualPercent] = useState('')

  const progressQuery = useQuery({
    queryKey: ['progress', projectId],
    queryFn: () => projectService.listProgress(projectId),
  })

  const createProgress = useMutation({
    mutationFn: () =>
      projectService.createProgress(projectId, {
        recordDate,
        plannedPercent: Number(plannedPercent),
        actualPercent: Number(actualPercent),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['progress', projectId] })
      queryClient.invalidateQueries({ queryKey: ['forecast', projectId] })
      setRecordDate('')
      setPlannedPercent('')
      setActualPercent('')
    },
  })

  if (progressQuery.isLoading) return <LoadingState label="Cargando avances…" />
  if (progressQuery.isError) {
    return <ErrorState description="No se pudieron cargar los avances." onRetry={() => progressQuery.refetch()} />
  }

  const columns: TableColumn<ProgressRecord>[] = [
    { key: 'date', header: 'Fecha', render: (row) => row.recordDate },
    { key: 'planned', header: 'Planeado %', render: (row) => row.plannedPercent },
    { key: 'actual', header: 'Real %', render: (row) => row.actualPercent },
  ]

  const records = progressQuery.data ?? []

  return (
    <div>
      <Card title="Registrar avance">
        <Input label="Fecha" type="date" value={recordDate} onChange={(event) => setRecordDate(event.target.value)} />
        <Input label="Planeado (%)" type="number" value={plannedPercent} onChange={(event) => setPlannedPercent(event.target.value)} />
        <Input label="Real (%)" type="number" value={actualPercent} onChange={(event) => setActualPercent(event.target.value)} />
        <Button
          disabled={!recordDate || plannedPercent === '' || actualPercent === '' || createProgress.isPending}
          loading={createProgress.isPending}
          onClick={() => createProgress.mutate()}
        >
          Registrar avance
        </Button>
      </Card>

      {records.length === 0 ? (
        <EmptyState icon="chart" title="Sin avances registrados" description="Registra el primer avance planeado vs. real de este proyecto." />
      ) : (
        <Table columns={columns} rows={records} getRowKey={(row) => row.id} />
      )}
    </div>
  )
}

export function ProgressPage() {
  return (
    <div>
      <h1 className="nx-dashboard__title">Avances de obra</h1>
      <RequiresActiveProject>{(projectId) => <ProgressList projectId={projectId} />}</RequiresActiveProject>
    </div>
  )
}
