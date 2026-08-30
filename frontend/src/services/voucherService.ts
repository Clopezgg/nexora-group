import { apiFetch, apiFetchBlob } from './httpClient'

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

export const voucherService = {
  listDocuments: (companyId: string) =>
    apiFetch<JournalDocumentOption[]>(
      `/accounting/journal-entries?companyId=${encodeURIComponent(companyId)}&limit=250`,
    ),

  download: async (
    accountingDocumentId: string,
    input: { beneficiary: string; payer: string; paymentMethod: string; approvedBy?: string },
  ): Promise<Blob> => {
    const params = new URLSearchParams({
      beneficiary: input.beneficiary,
      payer: input.payer,
      paymentMethod: input.paymentMethod,
    })
    if (input.approvedBy?.trim()) params.set('approvedBy', input.approvedBy.trim())
    const result = await apiFetchBlob(
      `/treasury/vouchers/${accountingDocumentId}?${params.toString()}`,
    )
    return result.blob
  },
}
