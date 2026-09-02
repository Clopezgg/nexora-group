import { apiFetch } from './httpClient'

export interface JournalDocumentOption {
  id: string
  documentNumber: string
  companyId: string
  scope: string
  projectId: string | null
  currencyCode: string
  status: string
  description: string | null
}

export interface InspectedLine {
  accountCode: string
  accountName: string
  debit: number
  credit: number
  description: string | null
  projectName: string | null
  costCenterName: string | null
}

export interface SourceEvent {
  kind: string
  label: string
  reference: string | null
  entityId: string | null
}

export interface Inspection {
  documentId: string
  documentNumber: string
  documentTypeCode: string
  scope: string
  status: string
  currencyCode: string
  description: string | null
  projectName: string | null
  postedAt: string | null
  totalDebit: number
  totalCredit: number
  balanced: boolean
  sourceEvent: SourceEvent
  lines: InspectedLine[]
  reversesDocumentId: string | null
  reversalReason: string | null
  reversedByDocumentIds: string[]
  evidence: Array<{ id: string; originalFilename: string; mimeType: string; sizeBytes: number }>
}

export interface DocumentLookupHit {
  domain: string
  entityType: string
  id: string
  number: string
  label: string
  status: string | null
  amount: string | null
  currencyCode: string | null
  party: string | null
  projectId: string | null
  accountingDocumentId: string | null
  exact: boolean
  allowedActions: string[]
}

export const transactionInspectorService = {
  /** Centro de Control por Número de Documento (§31/§32). */
  lookup: (q: string) =>
    apiFetch<{ query: string; results: DocumentLookupHit[] }>(
      `/accounting/documents/lookup?q=${encodeURIComponent(q)}`,
    ),

  /** Todos los asientos de la compañía — el inspector puede analizar
   * cualquier documento contable, no solo los egresos de tesorería. */
  listDocuments: (companyId: string) =>
    apiFetch<JournalDocumentOption[]>(
      `/accounting/journal-entries?companyId=${encodeURIComponent(companyId)}&limit=250`,
    ),

  inspect: (documentId: string) =>
    apiFetch<Inspection>(`/accounting/journal-entries/${documentId}/inspect`),
}
