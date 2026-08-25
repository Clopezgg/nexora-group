export interface Supplier {
  id: string
  companyId: string
  legalName: string
  tradeName: string | null
  taxId: string | null
  email: string | null
  phone: string | null
  status: string
  classification: string | null
}

export interface SupplierContract {
  id: string
  companyId: string
  supplierId: string
  projectId: string | null
  contractNumber: string
  scopeDescription: string | null
  value: string
  currencyCode: string
  startDate: string
  endDate: string | null
  advancePercentage: string
  retentionPercentage: string
  paymentTerms: string | null
  status: string
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

export interface GoodsReceipt {
  id: string
  receiptNumber: string
  purchaseOrderId: string
  warehouseId: string
  receivedAt: string
}
