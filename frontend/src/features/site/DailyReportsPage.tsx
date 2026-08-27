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
  Textarea,
  type TableColumn,
} from '../../design-system'
import { RequiresActiveProject } from '../projects/RequiresActiveProject'
import { documentService } from '../../services/documentService'
import { projectService } from '../../services/projectService'
import { siteReportService } from '../../services/siteReportService'
import type { DailySiteReport, DailySiteReportPhoto } from '../../types/siteReport'

const STATUS_TONE: Record<DailySiteReport['status'], 'neutral' | 'warning' | 'success' | 'danger'> = {
  DRAFT: 'neutral',
  SUBMITTED: 'warning',
  APPROVED: 'success',
  REJECTED: 'danger',
}

const STATUS_LABEL: Record<DailySiteReport['status'], string> = {
  DRAFT: 'Borrador',
  SUBMITTED: 'Enviado',
  APPROVED: 'Aprobado',
  REJECTED: 'Rechazado',
}

const EMPTY_FORM = {
  reportDate: '',
  weather: '',
  workforceSummary: '',
  activitiesPerformed: '',
  equipmentUsed: '',
  materialsUsed: '',
  incidents: '',
  observations: '',
}

function DailyReportsList({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient()
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [selectedReport, setSelectedReport] = useState<DailySiteReport | null>(null)

  const reportsQuery = useQuery({
    queryKey: ['site-reports', projectId],
    queryFn: () => siteReportService.list(projectId),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['site-reports', projectId] })

  const createMutation = useMutation({
    mutationFn: () =>
      siteReportService.create({
        projectId,
        reportDate: form.reportDate,
        weather: form.weather || undefined,
        workforceSummary: form.workforceSummary || undefined,
        activitiesPerformed: form.activitiesPerformed,
        equipmentUsed: form.equipmentUsed || undefined,
        materialsUsed: form.materialsUsed || undefined,
        incidents: form.incidents || undefined,
        observations: form.observations || undefined,
      }),
    onSuccess: () => {
      invalidate()
      setCreateModalOpen(false)
      setForm(EMPTY_FORM)
    },
  })

  const submitMutation = useMutation({
    mutationFn: (reportId: string) => siteReportService.submit(reportId),
    onSuccess: (report) => {
      invalidate()
      setSelectedReport(report)
    },
  })

  const approveMutation = useMutation({
    mutationFn: (reportId: string) => siteReportService.approve(reportId),
    onSuccess: (report) => {
      invalidate()
      setSelectedReport(report)
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (reportId: string) => siteReportService.reject(reportId),
    onSuccess: (report) => {
      invalidate()
      setSelectedReport(report)
    },
  })

  const columns: TableColumn<DailySiteReport>[] = [
    { key: 'reportDate', header: 'Fecha', render: (row) => row.reportDate },
    { key: 'weather', header: 'Clima', render: (row) => row.weather ?? '—' },
    {
      key: 'activities',
      header: 'Actividades',
      render: (row) => (row.activitiesPerformed.length > 60
        ? `${row.activitiesPerformed.slice(0, 60)}…`
        : row.activitiesPerformed),
    },
    {
      key: 'status',
      header: 'Estado',
      render: (row) => <Badge tone={STATUS_TONE[row.status]}>{STATUS_LABEL[row.status]}</Badge>,
    },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <Button variant="secondary" onClick={() => setSelectedReport(row)}>
          Ver detalle
        </Button>
      ),
    },
  ]

  const reports = reportsQuery.data ?? []

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Diario de obra</h1>
        <Button onClick={() => setCreateModalOpen(true)}>Nuevo reporte diario</Button>
      </header>

      <Card>
        {reportsQuery.isLoading ? (
          <LoadingState label="Cargando reportes diarios…" />
        ) : reportsQuery.isError ? (
          <ErrorState onRetry={() => reportsQuery.refetch()} />
        ) : reports.length === 0 ? (
          <EmptyState
            icon="notebook"
            title="Sin reportes diarios"
            description="Registra el primer reporte diario de este proyecto."
          />
        ) : (
          <Table
            columns={columns}
            rows={reports}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay reportes diarios."
          />
        )}
      </Card>

      <Modal open={createModalOpen} title="Nuevo reporte diario" onClose={() => setCreateModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Input
            label="Fecha"
            type="date"
            value={form.reportDate}
            onChange={(e) => setForm({ ...form, reportDate: e.target.value })}
            required
          />
          <Input
            label="Clima"
            value={form.weather}
            onChange={(e) => setForm({ ...form, weather: e.target.value })}
          />
          <Textarea
            label="Resumen de mano de obra"
            value={form.workforceSummary}
            onChange={(e) => setForm({ ...form, workforceSummary: e.target.value })}
          />
          <Textarea
            label="Actividades realizadas"
            value={form.activitiesPerformed}
            onChange={(e) => setForm({ ...form, activitiesPerformed: e.target.value })}
            required
          />
          <Textarea
            label="Equipo utilizado"
            value={form.equipmentUsed}
            onChange={(e) => setForm({ ...form, equipmentUsed: e.target.value })}
          />
          <Textarea
            label="Materiales utilizados"
            value={form.materialsUsed}
            onChange={(e) => setForm({ ...form, materialsUsed: e.target.value })}
          />
          <Textarea
            label="Incidentes"
            value={form.incidents}
            onChange={(e) => setForm({ ...form, incidents: e.target.value })}
          />
          <Textarea
            label="Observaciones"
            value={form.observations}
            onChange={(e) => setForm({ ...form, observations: e.target.value })}
          />
          <Button type="submit" loading={createMutation.isPending} disabled={!form.reportDate || !form.activitiesPerformed}>
            Guardar
          </Button>
          {createMutation.isError ? <p className="nx-field__error">{String(createMutation.error)}</p> : null}
        </form>
      </Modal>

      <ReportDetailModal
        report={selectedReport}
        projectId={projectId}
        onClose={() => setSelectedReport(null)}
        onSubmit={() => selectedReport && submitMutation.mutate(selectedReport.id)}
        onApprove={() => selectedReport && approveMutation.mutate(selectedReport.id)}
        onReject={() => selectedReport && rejectMutation.mutate(selectedReport.id)}
        actionPending={submitMutation.isPending || approveMutation.isPending || rejectMutation.isPending}
        actionError={submitMutation.error ?? approveMutation.error ?? rejectMutation.error}
        onPhotoAttached={() => {
          invalidate()
          if (selectedReport) {
            siteReportService.get(selectedReport.id).then(setSelectedReport)
          }
        }}
      />
    </div>
  )
}

function ReportDetailModal({
  report,
  projectId,
  onClose,
  onSubmit,
  onApprove,
  onReject,
  actionPending,
  actionError,
  onPhotoAttached,
}: {
  report: DailySiteReport | null
  projectId: string
  onClose: () => void
  onSubmit: () => void
  onApprove: () => void
  onReject: () => void
  actionPending: boolean
  actionError: unknown
  onPhotoAttached: () => void
}) {
  const [file, setFile] = useState<File | null>(null)

  const projectQuery = useQuery({
    queryKey: ['projects', 'detail', projectId],
    queryFn: () => projectService.get(projectId),
    enabled: Boolean(report),
  })

  const attachPhotoMutation = useMutation({
    mutationFn: async () => {
      if (!report) throw new Error('No hay reporte seleccionado')
      if (!file) throw new Error('Selecciona una foto')
      if (!projectQuery.data) throw new Error('No se pudo determinar la compañía del proyecto')
      const evidence = await documentService.uploadEvidence(projectQuery.data.companyId, file, 'SITE_PHOTO')
      return siteReportService.attachPhoto(report.id, evidence.id)
    },
    onSuccess: () => {
      setFile(null)
      onPhotoAttached()
    },
  })

  if (!report) return null

  return (
    <Modal open={Boolean(report)} title={`Reporte diario — ${report.reportDate}`} onClose={onClose}>
      <p><Badge tone={STATUS_TONE[report.status]}>{STATUS_LABEL[report.status]}</Badge></p>
      <dl className="nx-detail-list">
        <dt>Clima</dt>
        <dd>{report.weather ?? '—'}</dd>
        <dt>Mano de obra</dt>
        <dd>{report.workforceSummary ?? '—'}</dd>
        <dt>Actividades</dt>
        <dd>{report.activitiesPerformed}</dd>
        <dt>Equipo</dt>
        <dd>{report.equipmentUsed ?? '—'}</dd>
        <dt>Materiales</dt>
        <dd>{report.materialsUsed ?? '—'}</dd>
        <dt>Incidentes</dt>
        <dd>{report.incidents ?? '—'}</dd>
        <dt>Observaciones</dt>
        <dd>{report.observations ?? '—'}</dd>
      </dl>

      <h3>Fotos ({report.photos.length})</h3>
      {report.photos.length === 0 ? (
        <p>Sin fotos adjuntas todavía.</p>
      ) : (
        <ul>
          {report.photos.map((photo: DailySiteReportPhoto) => (
            <li key={photo.id}>Evidencia {photo.evidenceId.slice(0, 8)}…</li>
          ))}
        </ul>
      )}
      <form
        onSubmit={(event) => {
          event.preventDefault()
          attachPhotoMutation.mutate()
        }}
      >
        <Input
          label="Adjuntar foto (JPEG, PNG o WEBP)"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <Button type="submit" variant="secondary" loading={attachPhotoMutation.isPending} disabled={!file}>
          Subir foto
        </Button>
        {attachPhotoMutation.isError ? (
          <p className="nx-field__error">{String(attachPhotoMutation.error)}</p>
        ) : null}
      </form>

      <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
        {report.status === 'DRAFT' ? (
          <Button loading={actionPending} onClick={onSubmit}>
            Enviar para aprobación
          </Button>
        ) : null}
        {report.status === 'SUBMITTED' ? (
          <>
            <Button loading={actionPending} onClick={onApprove}>
              Aprobar
            </Button>
            <Button variant="ghost" disabled={actionPending} onClick={onReject}>
              Rechazar
            </Button>
          </>
        ) : null}
      </div>
      {actionError ? <p className="nx-field__error">{String(actionError)}</p> : null}
    </Modal>
  )
}

export function DailyReportsPage() {
  return (
    <div>
      <RequiresActiveProject>{(projectId) => <DailyReportsList projectId={projectId} />}</RequiresActiveProject>
    </div>
  )
}
