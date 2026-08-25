export const DOCUMENT_CATEGORIES = [
  'CONTRACT',
  'DRAWING',
  'PERMIT',
  'REPORT',
  'SAFETY',
  'QUALITY',
  'PHOTO',
  'OTHER',
] as const

export type DocumentCategory = (typeof DOCUMENT_CATEGORIES)[number]

export interface Evidence {
  id: string
  companyId: string
  blobKey: string
  originalFilename: string
  mimeType: string
  sizeBytes: number
  category: string | null
  entityType: string | null
  entityId: string | null
  uploadedBy: string
  createdAt: string
}

export interface DocumentVersion {
  id: string
  documentId: string
  versionNumber: number
  evidenceId: string
  status: 'ACTIVE' | 'SUPERSEDED'
  notes: string | null
  uploadedBy: string
  createdAt: string
}

export interface Document {
  id: string
  companyId: string
  scope: 'CENTRAL' | 'GENERAL' | 'PROJECT'
  projectId: string | null
  category: DocumentCategory
  title: string
  description: string | null
  status: 'ACTIVE' | 'ARCHIVED'
  currentVersion: DocumentVersion | null
}
