export interface Item {
  id: string
  companyId: string
  sku: string
  name: string
  itemType: string
  uom: string
  active: boolean
}

export interface Warehouse {
  id: string
  companyId: string
  projectId: string | null
  code: string
  name: string
  status: string
}

export interface StockPosition {
  itemId: string
  warehouseId: string
  quantityOnHand: string
  averageCost: string
}

export interface StockLedgerEntry {
  id: string
  itemId: string
  warehouseId: string
  movementType: string
  quantity: string
  unitCost: string
  resultingQtyOnHand: string
  resultingAvgCost: string
  projectId: string | null
  sourceType: string | null
  sourceId: string | null
  notes: string | null
}

export interface PhysicalCount {
  id: string
  warehouseId: string
  countDate: string
  status: string
}
