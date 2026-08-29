import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  Select,
  Table,
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { useMutationError } from '../../hooks/useMutationError'
import { documentService } from '../../services/documentService'
import { projectService } from '../../services/projectService'
import type { Evidence } from '../../types/document'
import type { WBSNode } from '../../types/project'

const EVIDENCE_CATEGORIES = [
  ['PHOTO', 'Fotografía'],
  ['PROGRESS', 'Avance'],
  ['QUALITY', 'Calidad'],
  ['SAFETY', 'Seguridad'],
  ['DAILY_REPORT', 'Diario de obra'],
  ['RECEIPT', 'Recepción'],
  ['OTHER', 'Otro evento'],
] as const

export function EvidencePage() {
  const queryClient = useQueryClient()
  const handleMutationError = useMutationError()
  const { companies, activeCompanyId, setActiveCompanyId, isLoading, isError, refetch } = useActiveCompany()
  const [projectId, setProjectId] = useState('')
  const [wbsNodeId, setWbsNodeId] = useState('')
  const [category, setCategory] = useState('PHOTO')
  const [file, setFile] = useState<File | null>(null)

  const projectsQuery = useQuery({
    queryKey: ['projects', activeCompanyId],
    queryFn: () => projectService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const wbsQuery = useQuery({
    queryKey: ['projects', projectId, 'wbs'],
    queryFn: () => projectService.listWbs(projectId),
    enabled: Boolean(projectId),
  })
  const evidenceQuery = useQuery({
    queryKey: ['evidence', activeCompanyId],
    queryFn: () => documentService.listEvidence(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const upload = useMutation({
    mutationFn: () => {
      if (!activeCompanyId || !file) throw new Error('Selecciona un archivo')
      const entityType = wbsNodeId ? 'WBS' : projectId ? 'PROJECT' : undefined
      const entityId = wbsNodeId || projectId || undefined
      return documentService.uploadEvidence(activeCompanyId, file, category, entityType, entityId)
    },
    onSuccess: () => {
      setFile(null)
      queryClient.invalidateQueries({ queryKey: ['evidence', activeCompanyId] })
    },
    onError: (error) => handleMutationError(error, 'Subir evidencia'),
  })

  if (isLoading) return <LoadingState label="Cargando evidencias…" />
  if (isError) return <ErrorState description="No se pudieron cargar las compañías." onRetry={() => refetch()} />
  if (companies.length === 0) {
    return <EmptyState icon="camera" title="No hay compañía configurada" description="Configura la compañía antes de cargar evidencias." />
  }

  const projects = Array.isArray(projectsQuery.data) ? projectsQuery.data : []
  const wbsNodes = Array.isArray(wbsQuery.data) ? wbsQuery.data : []
  const evidence = evidenceQuery.data ?? []
  const projectNames = new Map(projects.map((project) => [project.id, `${project.code ? `${project.code} — ` : ''}${project.name}`]))
  const wbsNames = new Map(wbsNodes.map((node) => [node.id, `${node.code} — ${node.name}`]))
  const categoryLabels = new Map<string, string>(EVIDENCE_CATEGORIES)

  const filteredEvidence = useMemo(() => {
    if (wbsNodeId) return evidence.filter((item) => item.entityType === 'WBS' && item.entityId === wbsNodeId)
    if (projectId) return evidence.filter((item) => (
      (item.entityType === 'PROJECT' && item.entityId === projectId)
      || (item.entityType === 'WBS' && wbsNodes.some((node) => node.id === item.entityId))
    ))
    return evidence
  }, [evidence, projectId, wbsNodeId, wbsNodes])

  const columns: TableColumn<Evidence>[] = [
    { key: 'file', header: 'Archivo', render: (row) => <strong>{row.originalFilename}</strong> },
    { key: 'category', header: 'Evento', render: (row) => <Badge>{categoryLabels.get(row.category ?? '') ?? row.category ?? 'Sin categoría'}</Badge> },
    {
      key: 'context',
      header: 'Contexto',
      render: (row) => {
        if (row.entityType === 'PROJECT' && row.entityId) return projectNames.get(row.entityId) ?? 'Proyecto'
        if (row.entityType === 'WBS' && row.entityId) return wbsNames.get(row.entityId) ?? 'WBS'
        return 'Empresa / general'
      },
    },
    { key: 'type', header: 'Tipo', render: (row) => row.mimeType },
    { key: 'size', header: 'Tamaño', render: (row) => `${Math.max(1, Math.round(row.sizeBytes / 1024))} KB` },
    { key: 'created', header: 'Cargado', render: (row) => new Date(row.createdAt).toLocaleString('es-HN') },
  ]

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <p className="nx-page__eyebrow">Control</p>
          <h1 className="nx-dashboard__title">Evidencias</h1>
          <p className="nx-field__hint">Fotos y archivos vinculados a proyecto, WBS, avance, calidad, seguridad, diario u otros eventos de obra.</p>
        </div>
      </header>

      <Card title="Contexto de evidencia">
        <Select value={activeCompanyId ?? ''} onChange={(event) => { setActiveCompanyId(event.target.value); setProjectId(''); setWbsNodeId('') }} label="Compañía">
          {companies.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
        </Select>
        <Select label="Proyecto" value={projectId} onChange={(event) => { setProjectId(event.target.value); setWbsNodeId('') }}>
          <option value="">Empresa / sin proyecto</option>
          {projects.map((project) => <option key={project.id} value={project.id}>{project.code ? `${project.code} — ` : ''}{project.name}</option>)}
        </Select>
        {projectId ? (
          <Select label="WBS (opcional)" value={wbsNodeId} onChange={(event) => setWbsNodeId(event.target.value)}>
            <option value="">Proyecto completo</option>
            {wbsNodes.map((node: WBSNode) => <option key={node.id} value={node.id}>{node.code} — {node.name}</option>)}
          </Select>
        ) : null}
        <Select label="Tipo de evidencia" value={category} onChange={(event) => setCategory(event.target.value)}>
          {EVIDENCE_CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </Select>
        <label className="nx-field">
          <span className="nx-field__label">Archivo</span>
          <input className="nx-input" type="file" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        </label>
        <Button loading={upload.isPending} disabled={!file} onClick={() => upload.mutate()}>Subir evidencia</Button>
      </Card>

      <Card title="Repositorio de evidencias">
        {evidenceQuery.isLoading ? <LoadingState label="Cargando archivos…" /> : evidenceQuery.isError ? (
          <ErrorState description="No se pudieron cargar las evidencias." onRetry={() => evidenceQuery.refetch()} />
        ) : (
          <Table columns={columns} rows={filteredEvidence} getRowKey={(row) => row.id} emptyMessage={projectId ? 'No hay evidencias para este contexto.' : 'Todavía no hay evidencias cargadas.'} />
        )}
      </Card>
    </div>
  )
}
