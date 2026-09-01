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
  /** INFLOW | OUTFLOW | INTERNAL_TRANSFER | NON_TREASURY. Los candidatos a
   * comprobante son siempre OUTFLOW (filtro server-side). */
  treasuryDirection?: string
  treasuryNet?: string
}

export interface BeneficiaryOption {
  beneficiaryType: 'SUPPLIER' | 'WORKER' | 'CUSTOMER'
  id: string
  name: string
  reference: string | null
}

export const voucherService = {
  /**
   * Documentos elegibles para Payment Voucher: EXCLUSIVAMENTE los OUTFLOW de
   * tesorería. El filtro es server-side (§17) — un ingreso (remesa, cobro,
   * aporte de capital, financiamiento) o una transferencia interna nunca
   * llega aquí. El backend además rechaza (422 NXR-VOUCHER-NOT-OUTFLOW) si
   * se intentara emitir un comprobante para un no-egreso.
   */
  listDocuments: (companyId: string) =>
    apiFetch<JournalDocumentOption[]>(
      `/treasury/voucher-candidates?companyId=${encodeURIComponent(companyId)}`,
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
      treasuryAccountId?: string
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
    if (input.treasuryAccountId) params.set('treasuryAccountId', input.treasuryAccountId)
    const result = await apiFetchBlob(
      `/treasury/vouchers/${accountingDocumentId}?${params.toString()}`,
    )
    return result.blob
  },
}
