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

export interface BeneficiaryOption {
  beneficiaryType: 'SUPPLIER' | 'WORKER' | 'CUSTOMER'
  id: string
  name: string
  reference: string | null
}

export const voucherService = {
  listDocuments: (companyId: string) =>
    apiFetch<JournalDocumentOption[]>(
      `/accounting/journal-entries?companyId=${encodeURIComponent(companyId)}&limit=250`,
    ),

  listBeneficiaries: (companyId: string) =>
    apiFetch<BeneficiaryOption[]>(
      `/treasury/beneficiaries?companyId=${encodeURIComponent(companyId)}`,
    ),

  download: async (
    accountingDocumentId: string,
    input: {
      beneficiaryType?: BeneficiaryOption['beneficiaryType']
      beneficiaryId?: string
      beneficiary?: string
      paymentMethod: string
      approvedBy?: string
    },
  ): Promise<Blob> => {
    // El pagador ya no se envía desde el cliente: es un dato fijo de la
    // compañía (Company Settings) que el backend resuelve. El beneficiario
    // se envía como (tipo, id) del registro real; el texto libre es fallback.
    const params = new URLSearchParams({ paymentMethod: input.paymentMethod })
    if (input.beneficiaryType && input.beneficiaryId) {
      params.set('beneficiaryType', input.beneficiaryType)
      params.set('beneficiaryId', input.beneficiaryId)
    } else if (input.beneficiary?.trim()) {
      params.set('beneficiary', input.beneficiary.trim())
    }
    if (input.approvedBy?.trim()) params.set('approvedBy', input.approvedBy.trim())
    const result = await apiFetchBlob(
      `/treasury/vouchers/${accountingDocumentId}?${params.toString()}`,
    )
    return result.blob
  },
}
