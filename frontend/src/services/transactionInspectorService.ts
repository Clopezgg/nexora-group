import { apiFetch } from './httpClient'

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

export const transactionInspectorService = {
  inspect: (documentId: string) =>
    apiFetch<Inspection>(`/accounting/journal-entries/${documentId}/inspect`),
}
