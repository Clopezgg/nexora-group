import type { RouteObject } from 'react-router-dom'
import { Navigate } from 'react-router-dom'
import { AppLayout } from '../layouts/AppLayout'
import { PermissionRoute } from '../features/auth/PermissionRoute'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { navItems } from './navigation'

type LazyRoute = NonNullable<RouteObject['lazy']>

const IMPLEMENTED_ROUTES: Record<string, LazyRoute> = {
  '/finanzas/control': async () => ({
    Component: (await import('../features/finance/FinancialControlCenterPage')).FinancialControlCenterPage,
  }),
  '/finanzas/contabilidad': async () => ({
    Component: (await import('../features/accounting/AccountingPage')).AccountingPage,
  }),
  '/finanzas/conciliacion-subledger': async () => ({
    Component: (await import('../features/finance/SubledgerReconciliationPage')).SubledgerReconciliationPage,
  }),
  '/finanzas/cierre': async () => ({
    Component: (await import('../features/finance/ClosingCenterPage')).ClosingCenterPage,
  }),
  '/finanzas/excepciones': async () => ({
    Component: (await import('../features/finance/ExceptionCenterPage')).ExceptionCenterPage,
  }),
  '/finanzas/inspector': async () => ({
    Component: (await import('../features/finance/TransactionInspectorPage')).TransactionInspectorPage,
  }),
  '/finanzas/flujo-13-semanas': async () => ({
    Component: (await import('../features/finance/CashForecastPage')).CashForecastPage,
  }),
  '/finanzas/tesoreria': async () => ({
    Component: (await import('../features/treasury/TreasuryPage')).TreasuryPage,
  }),
  '/finanzas/conciliacion': async () => ({
    Component: (await import('../features/treasury/AdvancedTreasuryPages')).BankReconciliationPage,
  }),
  '/finanzas/cierres-caja': async () => ({
    Component: (await import('../features/treasury/AdvancedTreasuryPages')).CashClosingsPage,
  }),
  '/finanzas/restricciones-fondos': async () => ({
    Component: (await import('../features/treasury/AdvancedTreasuryPages')).FundRestrictionsPage,
  }),
  '/finanzas/comprobantes': async () => ({
    Component: (await import('../features/treasury/VouchersPage')).VouchersPage,
  }),
  '/finanzas/cuentas-por-pagar': async () => ({
    Component: (await import('../features/treasury/AccountsPayableWorkspace')).AccountsPayableWorkspace,
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
  '/proyectos/cockpit': async () => ({
    Component: (await import('../features/projects/ProjectCockpitPage')).ProjectCockpitPage,
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
    Component: (await import('../features/documents/EvidencePage')).EvidencePage,
  }),
  '/control/auditoria': async () => ({
    Component: (await import('../features/audit/AuditLogPage')).AuditLogPage,
  }),
  '/control/configuracion': async () => ({
    Component: (await import('../features/settings/CompanySettingsWorkspace')).CompanySettingsWorkspace,
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
    Component: (await import('../features/commercial/BillingPage')).BillingPage,
  }),
  '/comercial/cobros': async () => ({
    Component: (await import('../features/commercial/CollectionsPage')).CollectionsPage,
  }),
}

const applicationRoutes: RouteObject[] = navItems
  .filter((item) => item.path !== '/inicio')
  .map((item) => {
    const lazy = IMPLEMENTED_ROUTES[item.path]
    return lazy
      ? {
          element: <PermissionRoute requiredAny={item.requiredAny ?? []} />,
          children: [{ path: item.path.replace(/^\//, ''), lazy }],
        }
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
            element: <PermissionRoute requiredAny={['project:read']} />,
            children: [
              {
                path: 'proyectos/:projectId',
                lazy: async () => ({
                  Component: (await import('../features/projects/ProjectDetailPage'))
                    .ProjectDetailPage,
                }),
              },
            ],
          },
          ...applicationRoutes,
        ],
      },
    ],
  },
  { path: '*', element: <Navigate to="/inicio" replace /> },
]
