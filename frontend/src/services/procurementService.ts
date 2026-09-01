import { apiFetch } from './httpClient'
import type {
  GoodsReceipt,
  PurchaseOrder,
  Quotation,
  Requisition,
  Rfq,
  Supplier,
  SupplierContract,
  SupplierContractCategory,
} from '../types/procurement'

export const procurementService = {
  listSuppliers: (companyId: string) =>
    apiFetch<Supplier[]>(`/procurement/suppliers?company_id=${companyId}`),
  createSupplier: (payload: {
    companyId: string
    legalName: string
    tradeName?: string
    taxId?: string
    addressLine1?: string
    addressLine2?: string
    city?: string
    stateDepartment?: string
    country?: string
  }) =>
    apiFetch<Supplier>('/procurement/suppliers', { method: 'POST', body: JSON.stringify(payload) }),

  listContracts: (companyId: string) =>
    apiFetch<SupplierContract[]>(`/procurement/suppliers/contracts?company_id=${companyId}`),
  createContract: (payload: {
    companyId: string
    supplierId: string
    projectId?: string
    contractNumber: string
    contractCategory?: SupplierContractCategory
    value: string
    currencyCode: string
    startDate: string
    endDate?: string
    advancePercentage?: string
    retentionPercentage?: string
    scopeDescription?: string
  }) =>
    apiFetch<SupplierContract>('/procurement/suppliers/contracts', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listRequisitions: (companyId: string) =>
    apiFetch<Requisition[]>(`/procurement/requisitions?company_id=${companyId}`),
  createRequisition: (payload: {
    companyId: string
    justification?: string
    priority?: string
    lines: { description: string; quantity: string; estimatedUnitCost?: string }[]
  }) => apiFetch<Requisition>('/procurement/requisitions', { method: 'POST', body: JSON.stringify(payload) }),
  approveRequisition: (id: string) =>
    apiFetch<Requisition>(`/procurement/requisitions/${id}/approve`, { method: 'POST' }),

  listPurchaseOrders: (companyId: string) =>
    apiFetch<PurchaseOrder[]>(`/procurement/purchase-orders?company_id=${companyId}`),
  createPurchaseOrder: (payload: {
    companyId: string
    supplierId: string
    currencyCode: string
    lines: { description: string; quantity: string; unitPrice: string }[]
  }) => apiFetch<PurchaseOrder>('/procurement/purchase-orders', { method: 'POST', body: JSON.stringify(payload) }),
  approvePurchaseOrder: (id: string) =>
    apiFetch<PurchaseOrder>(`/procurement/purchase-orders/${id}/approve`, { method: 'POST' }),
  sendPurchaseOrder: (id: string) =>
    apiFetch<PurchaseOrder>(`/procurement/purchase-orders/${id}/send`, { method: 'POST' }),

  listRfqs: (companyId: string) => apiFetch<Rfq[]>(`/procurement/rfqs?company_id=${companyId}`),
  createRfq: (payload: { companyId: string; supplierIds: string[]; dueDate?: string; terms?: string }) =>
    apiFetch<Rfq>('/procurement/rfqs', { method: 'POST', body: JSON.stringify(payload) }),
  listQuotations: (rfqId: string) => apiFetch<Quotation[]>(`/procurement/rfqs/${rfqId}/quotations`),
  createQuotation: (
    rfqId: string,
    payload: {
      supplierId: string
      currencyCode: string
      deliveryDays?: number
      paymentTerms?: string
      validUntil?: string
      lines: { description: string; quantity: string; unitPrice: string }[]
    },
  ) =>
    apiFetch<Quotation>(`/procurement/rfqs/${rfqId}/quotations`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createPurchaseOrderFromQuotation: (payload: {
    companyId: string
    supplierQuotationId: string
    projectId?: string
  }) =>
    apiFetch<PurchaseOrder>('/procurement/purchase-orders/from-quotation', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  listGoodsReceipts: (purchaseOrderId: string) =>
    apiFetch<GoodsReceipt[]>(`/procurement/goods-receipts?purchase_order_id=${purchaseOrderId}`),
  createGoodsReceipt: (payload: {
    purchaseOrderId: string
    warehouseId: string
    receivedAt: string
    lines: { purchaseOrderLineId: string; quantityReceived: string }[]
  }) => apiFetch<GoodsReceipt>('/procurement/goods-receipts', { method: 'POST', body: JSON.stringify(payload) }),
}
