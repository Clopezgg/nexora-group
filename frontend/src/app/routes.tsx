import type { RouteObject } from 'react-router-dom'
import { Navigate } from 'react-router-dom'
import { AppLayout } from '../layouts/AppLayout'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { LoginPage } from '../pages/LoginPage'
import { HomePage } from '../features/home/HomePage'
import { PlaceholderPage } from '../pages/PlaceholderPage'
import { TreasuryPage } from '../features/treasury/TreasuryPage'
import { AccountsPayablePage } from '../features/treasury/AccountsPayablePage'
import { AccountsReceivablePage } from '../features/treasury/AccountsReceivablePage'
import { GoodsReceiptsPage } from '../features/procurement/GoodsReceiptsPage'
import { PurchaseOrdersPage } from '../features/procurement/PurchaseOrdersPage'
import { RequisitionsPage } from '../features/procurement/RequisitionsPage'
import { SuppliersPage } from '../features/procurement/SuppliersPage'
import { InventoryPage } from '../features/inventory/InventoryPage'
import { WarehousesPage } from '../features/inventory/WarehousesPage'
import { BudgetPage } from '../features/projects/BudgetPage'
import { ChangeOrdersPage } from '../features/projects/ChangeOrdersPage'
import { ProgressPage } from '../features/projects/ProgressPage'
import { ProjectsPage } from '../features/projects/ProjectsPage'
import { WBSPage } from '../features/projects/WBSPage'
import { navItems } from './navigation'

// Track A (Financial Core), Track B (Project Control) y Track C (Supply
// Chain) implementan estas rutas; el resto de navItems sigue como
// PlaceholderPage hasta que su track dueño aterrice.
const IMPLEMENTED_ROUTES: Record<string, RouteObject['element']> = {
  '/finanzas/tesoreria': <TreasuryPage />,
  '/finanzas/cuentas-por-pagar': <AccountsPayablePage />,
  '/finanzas/cuentas-por-cobrar': <AccountsReceivablePage />,
  '/proyectos': <ProjectsPage />,
  '/proyectos/wbs': <WBSPage />,
  '/proyectos/presupuestos': <BudgetPage />,
  '/proyectos/ordenes-de-cambio': <ChangeOrdersPage />,
  '/proyectos/avances': <ProgressPage />,
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
    element: IMPLEMENTED_ROUTES[item.path] ?? <PlaceholderPage title={item.label} />,
  }))

export const routes: RouteObject[] = [
  { path: '/', element: <Navigate to="/inicio" replace /> },
  { path: '/login', element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [{ path: 'inicio', element: <HomePage /> }, ...placeholderRoutes],
      },
    ],
  },
  { path: '*', element: <Navigate to="/inicio" replace /> },
]
