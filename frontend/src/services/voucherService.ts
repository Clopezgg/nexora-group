import { ApiError, apiFetch } from './httpClient'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

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
    const response = await fetch(
      `${API_BASE_URL}/treasury/vouchers/${accountingDocumentId}?${params.toString()}`,
      { credentials: 'include' },
    )
    if (!response.ok) {
      let message = `Error ${response.status}`
      try {
        const body = await response.json()
        message = body.detail ?? body.error?.message ?? message
      } catch {
        // PDF endpoint can return a non-JSON failure from the proxy.
      }
      throw new ApiError(message, response.status)
    }
    return response.blob()
  },
}