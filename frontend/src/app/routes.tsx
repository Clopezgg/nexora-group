import type { RouteObject } from 'react-router-dom'
import { Navigate } from 'react-router-dom'
import { AppLayout } from '../layouts/AppLayout'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { LoginPage } from '../pages/LoginPage'
import { HomePage } from '../features/home/HomePage'
import { PlaceholderPage } from '../pages/PlaceholderPage'
import { GoodsReceiptsPage } from '../features/procurement/GoodsReceiptsPage'
import { PurchaseOrdersPage } from '../features/procurement/PurchaseOrdersPage'
import { RequisitionsPage } from '../features/procurement/RequisitionsPage'
import { SuppliersPage } from '../features/procurement/SuppliersPage'
import { InventoryPage } from '../features/inventory/InventoryPage'
import { WarehousesPage } from '../features/inventory/WarehousesPage'
import { navItems } from './navigation'

// Track C -- Supply Chain: estas rutas ya tienen pantalla real, reemplazan
// el PlaceholderPage genérico. El resto de rutas de abastecimiento (RFQ,
// cotizaciones, comparativos, contratos) tienen backend real pero todavía
// no UI -- siguen en EmptyState honesto hasta que se construya su pantalla.
const realPageByPath: Record<string, RouteObject['element']> = {
  '/abastecimiento/solicitudes': <RequisitionsPage />,
  '/abastecimiento/ordenes-de-compra': <PurchaseOrdersPage />,
  '/abastecimiento/recepciones': <GoodsReceiptsPage />,
  '/abastecimiento/inventario': <InventoryPage />,
  '/abastecimiento/almacenes': <WarehousesPage />,
  '/abastecimiento/proveedores': <SuppliersPage />,
}

const placeholderRoutes: RouteObject[] = navItems
  .filter((item) => item.path !== '/inicio')
  .map((item) => ({
    path: item.path.replace(/^\//, ''),
    element: realPageByPath[item.path] ?? <PlaceholderPage title={item.label} />,
  }))

export const routes: RouteObject[] = [
  { path: '/', element: <Navigate to="/inicio" replace /> },
  { path: '/login', element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: 'inicio', element: <HomePage /> },
          ...placeholderRoutes,
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/inicio" replace /> },
]
