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
  type TableColumn,
} from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { documentService } from '../../services/documentService'
import { DOCUMENT_CATEGORIES, type Document, type DocumentVersion } from '../../types/document'

const STATUS_TONE: Record<Document['status'], 'success' | 'neutral'> = {
  ACTIVE: 'success',
  ARCHIVED: 'neutral',
}

const VERSION_STATUS_TONE: Record<DocumentVersion['status'], 'success' | 'neutral'> = {
  ACTIVE: 'success',
  SUPERSEDED: 'neutral',
}

export function DocumentsPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const queryClient = useQueryClient()
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)

  const documentsQuery = useQuery({
    queryKey: ['documents', 'list', activeCompanyId],
    queryFn: () => documentService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const columns: TableColumn<Document>[] = [
    { key: 'title', header: 'Documento', render: (row) => row.title },
    { key: 'category', header: 'Categoría', render: (row) => row.category },
    {
      key: 'version',
      header: 'Versión actual',
      render: (row) => (row.currentVersion ? `v${row.currentVersion.versionNumber}` : '—'),
    },
    { key: 'status', header: 'Estado', render: (row) => <Badge tone={STATUS_TONE[row.status]}>{row.status}</Badge> },
    {
      key: 'actions',
      header: '',
      render: (row) => (
        <Button variant="secondary" onClick={() => setSelectedDocument(row)}>
          Ver versiones
        </Button>
      ),
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="🗂️"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Documentos</h1>
        <Button onClick={() => setCreateModalOpen(true)}>Nuevo documento</Button>
      </header>

      <Card>
        {documentsQuery.isLoading ? (
          <LoadingState label="Cargando documentos…" />
        ) : documentsQuery.isError ? (
          <ErrorState onRetry={() => documentsQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={documentsQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay documentos registrados."
          />
        )}
      </Card>

      <CreateDocumentModal
        open={createModalOpen}
        companyId={activeCompanyId}
        onClose={() => setCreateModalOpen(false)}
        onCreated={() => {
          queryClient.invalidateQueries({ queryKey: ['documents', 'list', activeCompanyId] })
          setCreateModalOpen(false)
        }}
      />

      <DocumentVersionsModal
        document={selectedDocument}
        companyId={activeCompanyId}
        onClose={() => setSelectedDocument(null)}
        onVersionAdded={() => {
          queryClient.invalidateQueries({ queryKey: ['documents', 'list', activeCompanyId] })
          queryClient.invalidateQueries({ queryKey: ['documents', 'versions', selectedDocument?.id] })
        }}
      />
    </div>
  )
}

function CreateDocumentModal({
  open,
  companyId,
  onClose,
  onCreated,
}: {
  open: boolean
  companyId: string
  onClose: () => void
  onCreated: () => void
}) {
  const [form, setForm] = useState({ title: '', category: 'OTHER', description: '' })
  const [file, setFile] = useState<File | null>(null)

  const createMutation = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error('Selecciona un archivo')
      const evidence = await documentService.uploadEvidence(companyId, file, form.category)
      return documentService.create({
        companyId,
        scope: 'GENERAL',
        category: form.category,
        title: form.title,
        description: form.description || undefined,
        evidenceId: evidence.id,
      })
    },
    onSuccess: () => {
      setForm({ title: '', category: 'OTHER', description: '' })
      setFile(null)
      onCreated()
    },
  })

  return (
    <Modal open={open} title="Nuevo documento" onClose={onClose}>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          createMutation.mutate()
        }}
      >
        <Input label="Título" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
        <Select label="Categoría" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
          {DOCUMENT_CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {category}
            </option>
          ))}
        </Select>
        <Input
          label="Descripción"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
        />
        <Input
          label="Archivo (PDF, JPEG, PNG o WEBP)"
          type="file"
          accept="application/pdf,image/jpeg,image/png,image/webp"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          required
        />
        <Button type="submit" loading={createMutation.isPending} disabled={!file}>
          Guardar
        </Button>
        {createMutation.isError ? <p className="nx-field__error">{String(createMutation.error)}</p> : null}
      </form>
    </Modal>
  )
}

function DocumentVersionsModal({
  document,
  companyId,
  onClose,
  onVersionAdded,
}: {
  document: Document | null
  companyId: string
  onClose: () => void
  onVersionAdded: () => void
}) {
  const [notes, setNotes] = useState('')
  const [file, setFile] = useState<File | null>(null)

  const versionsQuery = useQuery({
    queryKey: ['documents', 'versions', document?.id],
    queryFn: () => documentService.listVersions(document!.id),
    enabled: Boolean(document),
  })

  const addVersionMutation = useMutation({
    mutationFn: async () => {
      if (!document) throw new Error('No hay documento seleccionado')
      if (!file) throw new Error('Selecciona un archivo')
      const evidence = await documentService.uploadEvidence(companyId, file, document.category)
      return documentService.addVersion(document.id, { evidenceId: evidence.id, notes: notes || undefined })
    },
    onSuccess: () => {
      setNotes('')
      setFile(null)
      onVersionAdded()
    },
  })

  return (
    <Modal open={Boolean(document)} title={document ? `Versiones — ${document.title}` : ''} onClose={onClose}>
      {versionsQuery.isLoading ? (
        <LoadingState label="Cargando versiones…" />
      ) : (
        <ul>
          {(versionsQuery.data ?? []).map((version) => (
            <li key={version.id}>
              v{version.versionNumber} —{' '}
              <Badge tone={VERSION_STATUS_TONE[version.status]}>{version.status}</Badge>
              {version.notes ? ` — ${version.notes}` : ''}
            </li>
          ))}
          {(versionsQuery.data ?? []).length === 0 ? <li>Sin versiones todavía.</li> : null}
        </ul>
      )}

      <form
        onSubmit={(event) => {
          event.preventDefault()
          addVersionMutation.mutate()
        }}
      >
        <Input
          label="Nueva versión (PDF, JPEG, PNG o WEBP)"
          type="file"
          accept="application/pdf,image/jpeg,image/png,image/webp"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          required
        />
        <Input label="Notas" value={notes} onChange={(e) => setNotes(e.target.value)} />
        <Button type="submit" loading={addVersionMutation.isPending} disabled={!file}>
          Subir nueva versión
        </Button>
        {addVersionMutation.isError ? (
          <p className="nx-field__error">{String(addVersionMutation.error)}</p>
        ) : null}
      </form>
    </Modal>
  )
}
