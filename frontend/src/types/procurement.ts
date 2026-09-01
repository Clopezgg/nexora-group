export type SupplierPartyRole = 'SUPPLIER' | 'CONTRACTOR' | 'BOTH'
export type SupplierStatus = 'ACTIVE' | 'INACTIVE' | 'BLOCKED' | 'ARCHIVED'

export interface Supplier {
  id: string
  companyId: string
  legalName: string
  tradeName: string | null
  taxId: string | null
  contactName?: string | null
  email: string | null
  phone: string | null
  address: string | null
  addressLine1: string | null
  addressLine2: string | null
  city: string | null
  stateDepartment: string | null
  country: string | null
  status: string
  partyRole: SupplierPartyRole
  classification: string | null
  paymentTerms?: string | null
}

export type SupplierContractCategory =
  | 'LABOR'
  | 'SUBCONTRACT'
  | 'MATERIALS'
  | 'EQUIPMENT'
  | 'PROFESSIONAL_SERVICES'
  | 'OTHER'

/** UX en español para `SupplierContractCategory` (ORDEN MAESTRA §13). */
export const SUPPLIER_CONTRACT_CATEGORY_LABELS: Record<SupplierContractCategory, string> = {
  LABOR: 'Mano de obra',
  SUBCONTRACT: 'Subcontrato',
  MATERIALS: 'Materiales',
  EQUIPMENT: 'Equipo',
  PROFESSIONAL_SERVICES: 'Servicios profesionales',
  OTHER: 'Otro',
}

export interface SupplierContract {
  id: string
  companyId: string
  supplierId: string
  projectId: string | null
  contractNumber: string
  contractCategory: SupplierContractCategory
  scopeDescription: string | null
  value: string
  currencyCode: string
  startDate: string
  endDate: string | null
  advancePercentage: string
  retentionPercentage: string
  paymentTerms: string | null
  paymentTermsType: SupplierContractPaymentTermsType
  status: string
}

/** §6/§18 — modo de pago contractual explícito. */
export type SupplierContractPaymentTermsType = 'LUMP_SUM' | 'MONTHLY' | 'CUSTOM'

export const SUPPLIER_CONTRACT_PAYMENT_TERMS_LABELS: Record<SupplierContractPaymentTermsType, string> = {
  LUMP_SUM: 'Pago único / suma alzada',
  MONTHLY: 'Cuotas mensuales',
  CUSTOM: 'Cuotas personalizadas',
}

export interface RequisitionLine {
  id: string
  itemId: string | null
  description: string
  quantity: string
  estimatedUnitCost: string
}

export interface Requisition {
  id: string
  companyId: string
  requisitionNumber: string
  projectId: string | null
  justification: string | null
  priority: string
  requiredDate: string | null
  status: string
  lines: RequisitionLine[]
}

export interface PurchaseOrderLine {
  id: string
  itemId: string | null
  description: string
  quantity: string
  unitPrice: string
  taxAmount: string
  quantityReceived: string
}

export interface PurchaseOrder {
  id: string
  companyId: string
  poNumber: string
  supplierId: string
  projectId: string | null
  currencyCode: string
  status: string
  lines: PurchaseOrderLine[]
}

export interface Rfq {
  id: string
  rfqNumber: string
  purchaseRequisitionId: string | null
  dueDate: string | null
  status: string
}

export interface QuotationLine {
  id: string
  description: string
  quantity: string
  unitPrice: string
  taxAmount: string
}

export interface Quotation {
  id: string
  requestForQuotationId: string
  supplierId: string
  currencyCode: string
  status: string
  total: string
  deliveryDays: number | null
  paymentTerms: string | null
  validUntil: string | null
  notes: string | null
  lines: QuotationLine[]
}

export interface GoodsReceipt {
  id: string
  receiptNumber: string
  purchaseOrderId: string
  warehouseId: string
  receivedAt: string
}
