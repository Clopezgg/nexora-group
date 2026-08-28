import type { RouteObject } from 'react-router-dom'
import { Navigate } from 'react-router-dom'
import { AppLayout } from '../layouts/AppLayout'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { navItems } from './navigation'

type LazyRoute = NonNullable<RouteObject['lazy']>

const IMPLEMENTED_ROUTES: Record<string, LazyRoute> = {
  '/finanzas/contabilidad': async () => ({
    Component: (await import('../features/accounting/AccountingPage')).AccountingPage,
  }),
  '/finanzas/tesoreria': async () => ({
    Component: (await import('../features/treasury/TreasuryPage')).TreasuryPage,
  }),
  '/finanzas/cuentas-por-pagar': async () => ({
    Component: (await import('../features/treasury/AccountsPayablePage')).AccountsPayablePage,
  }),
  '/finanzas/cuentas-por-cobrar': async () => ({
    Component: (await import('../features/treasury/AccountsReceivablePage')).AccountsReceivablePage,
  }),
  '/finanzas/activos': async () => ({
    Component: (await import('../features/assets/FixedAssetsPage')).FixedAssetsPage,
  }),
  '/proyectos': async () => ({
    Component: (await import('../features/projects/ProjectsPage')).ProjectsPage,
  }),
  '/proyectos/wbs': async () => ({
    Component: (await import('../features/projects/WBSPage')).WBSPage,
  }),
  '/proyectos/presupuestos': async () => ({
    Component: (await import('../features/projects/BudgetPage')).BudgetPage,
  }),
  '/proyectos/ordenes-de-cambio': async () => ({
    Component: (await import('../features/projects/ChangeOrdersPage')).ChangeOrdersPage,
  }),
  '/proyectos/avances': async () => ({
    Component: (await import('../features/projects/ProgressPage')).ProgressPage,
  }),
  '/proyectos/rfi-submittals': async () => ({
    Component: (await import('../features/rfi/RfiSubmittalsPage')).RfiSubmittalsPage,
  }),
  '/abastecimiento/solicitudes': async () => ({
    Component: (await import('../features/procurement/RequisitionsPage')).RequisitionsPage,
  }),
  '/abastecimiento/ordenes-de-compra': async () => ({
    Component: (await import('../features/procurement/PurchaseOrdersPage')).PurchaseOrdersPage,
  }),
  '/abastecimiento/recepciones': async () => ({
    Component: (await import('../features/procurement/GoodsReceiptsPage')).GoodsReceiptsPage,
  }),
  '/abastecimiento/inventario': async () => ({
    Component: (await import('../features/inventory/InventoryPage')).InventoryPage,
  }),
  '/abastecimiento/almacenes': async () => ({
    Component: (await import('../features/inventory/WarehousesPage')).WarehousesPage,
  }),
  '/abastecimiento/proveedores': async () => ({
    Component: (await import('../features/procurement/SuppliersPage')).SuppliersPage,
  }),
  '/abastecimiento/contratos': async () => ({
    Component: (await import('../features/procurement/SupplierContractsPage')).SupplierContractsPage,
  }),
  '/abastecimiento/comparativos': async () => ({
    Component: (await import('../features/procurement/BidComparisonPage')).BidComparisonPage,
  }),
  '/recursos/personal': async () => ({
    Component: (await import('../features/workforce/WorkersPage')).WorkersPage,
  }),
  '/recursos/cuadrillas': async () => ({
    Component: (await import('../features/workforce/CrewsPage')).CrewsPage,
  }),
  '/recursos/tiempo': async () => ({
    Component: (await import('../features/workforce/TimeEntriesPage')).TimeEntriesPage,
  }),
  '/recursos/equipos': async () => {
    const { EquipmentPage } = await import('../features/equipment/EquipmentPage')
    return { Component: () => <EquipmentPage defaultTab="equipos" /> }
  },
  '/recursos/combustible': async () => {
    const { EquipmentPage } = await import('../features/equipment/EquipmentPage')
    return { Component: () => <EquipmentPage defaultTab="combustible" /> }
  },
  '/recursos/mantenimiento': async () => {
    const { EquipmentPage } = await import('../features/equipment/EquipmentPage')
    return { Component: () => <EquipmentPage defaultTab="mantenimiento" /> }
  },
  '/control/documentos': async () => ({
    Component: (await import('../features/documents/DocumentsPage')).DocumentsPage,
  }),
  '/control/evidencias': async () => ({
    Component: (await import('../features/documents/DocumentsPage')).DocumentsPage,
  }),
  '/control/auditoria': async () => ({
    Component: (await import('../features/audit/AuditLogPage')).AuditLogPage,
  }),
  '/control/configuracion': async () => ({
    Component: (await import('../features/settings/CompanySettingsPage')).CompanySettingsPage,
  }),
  '/control/reportes': async () => ({
    Component: (await import('../features/reports/ReportsPage')).ReportsPage,
  }),
  '/inicio/aprobaciones': async () => ({
    Component: (await import('../features/approvals/ApprovalInboxPage')).ApprovalInboxPage,
  }),
  '/proyectos/diario-de-obra': async () => ({
    Component: (await import('../features/site/DailyReportsPage')).DailyReportsPage,
  }),
  '/proyectos/calidad': async () => ({
    Component: (await import('../features/quality/QualityPage')).QualityPage,
  }),
  '/proyectos/seguridad': async () => ({
    Component: (await import('../features/safety/SafetyPage')).SafetyPage,
  }),
  '/comercial/leads': async () => ({
    Component: (await import('../features/commercial/LeadsPage')).LeadsPage,
  }),
  '/comercial/oportunidades': async () => ({
    Component: (await import('../features/commercial/OpportunitiesPage')).OpportunitiesPage,
  }),
  '/comercial/clientes': async () => ({
    Component: (await import('../features/commercial/CustomersPage')).CustomersPage,
  }),
  '/comercial/cotizaciones': async () => ({
    Component: (await import('../features/commercial/QuotationsPage')).QuotationsPage,
  }),
  '/comercial/contratos': async () => ({
    Component: (await import('../features/commercial/SalesContractsPage')).SalesContractsPage,
  }),
  '/comercial/facturacion': async () => ({
    Component: (await import('../features/treasury/AccountsReceivablePage')).AccountsReceivablePage,
  }),
  '/comercial/cobros': async () => ({
    Component: (await import('../features/treasury/AccountsReceivablePage')).AccountsReceivablePage,
  }),
}

const applicationRoutes: RouteObject[] = navItems
  .filter((item) => item.path !== '/inicio')
  .map((item) => {
    const lazy = IMPLEMENTED_ROUTES[item.path]
    return lazy
      ? { path: item.path.replace(/^\//, ''), lazy }
      : { path: item.path.replace(/^\//, ''), element: <Navigate to="/inicio" replace /> }
  })

export const routes: RouteObject[] = [
  { path: '/', element: <Navigate to="/inicio" replace /> },
  {
    path: '/login',
    lazy: async () => ({ Component: (await import('../pages/LoginPage')).LoginPage }),
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            path: 'inicio',
            lazy: async () => ({
              Component: (await import('../features/home/HomePage')).HomePage,
            }),
          },
          {
            path: 'proyectos/:projectId',
            lazy: async () => ({
              Component: (await import('../features/projects/ProjectDetailPage')).ProjectDetailPage,
            }),
          },
          ...applicationRoutes,
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/inicio" replace /> },
]
