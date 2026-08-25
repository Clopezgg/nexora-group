import { apiFetch } from './httpClient'
import type { GoodsReceipt, PurchaseOrder, Requisition, Supplier } from '../types/procurement'

export const procurementService = {
  listSuppliers: (companyId: string) =>
    apiFetch<Supplier[]>(`/procurement/suppliers?company_id=${companyId}`),
  createSupplier: (payload: { companyId: string; legalName: string; tradeName?: string; taxId?: string }) =>
    apiFetch<Supplier>('/procurement/suppliers', { method: 'POST', body: JSON.stringify(payload) }),

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

  listGoodsReceipts: (purchaseOrderId: string) =>
    apiFetch<GoodsReceipt[]>(`/procurement/goods-receipts?purchase_order_id=${purchaseOrderId}`),
  createGoodsReceipt: (payload: {
    purchaseOrderId: string
    warehouseId: string
    receivedAt: string
    lines: { purchaseOrderLineId: string; quantityReceived: string }[]
  }) => apiFetch<GoodsReceipt>('/procurement/goods-receipts', { method: 'POST', body: JSON.stringify(payload) }),
}
