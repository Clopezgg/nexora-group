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
