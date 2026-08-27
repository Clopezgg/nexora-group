import type { RouteObject } from 'react-router-dom'
import { Navigate } from 'react-router-dom'
import { AppLayout } from '../layouts/AppLayout'
import { ProtectedRoute } from '../features/auth/ProtectedRoute'
import { LoginPage } from '../pages/LoginPage'
import { HomePage } from '../features/home/HomePage'
import { TreasuryPage } from '../features/treasury/TreasuryPage'
import { AccountsPayablePage } from '../features/treasury/AccountsPayablePage'
import { AccountsReceivablePage } from '../features/treasury/AccountsReceivablePage'
import { GoodsReceiptsPage } from '../features/procurement/GoodsReceiptsPage'
import { PurchaseOrdersPage } from '../features/procurement/PurchaseOrdersPage'
import { RequisitionsPage } from '../features/procurement/RequisitionsPage'
import { SuppliersPage } from '../features/procurement/SuppliersPage'
import { SupplierContractsPage } from '../features/procurement/SupplierContractsPage'
import { BidComparisonPage } from '../features/procurement/BidComparisonPage'
import { InventoryPage } from '../features/inventory/InventoryPage'
import { WarehousesPage } from '../features/inventory/WarehousesPage'
import { BudgetPage } from '../features/projects/BudgetPage'
import { ChangeOrdersPage } from '../features/projects/ChangeOrdersPage'
import { ProgressPage } from '../features/projects/ProgressPage'
import { ProjectsPage } from '../features/projects/ProjectsPage'
import { WBSPage } from '../features/projects/WBSPage'
import { FixedAssetsPage } from '../features/assets/FixedAssetsPage'
import { EquipmentPage } from '../features/equipment/EquipmentPage'
import { WorkersPage } from '../features/workforce/WorkersPage'
import { CrewsPage } from '../features/workforce/CrewsPage'
import { TimeEntriesPage } from '../features/workforce/TimeEntriesPage'
import { DocumentsPage } from '../features/documents/DocumentsPage'
import { AuditLogPage } from '../features/audit/AuditLogPage'
import { ReportsPage } from '../features/reports/ReportsPage'
import { ApprovalInboxPage } from '../features/approvals/ApprovalInboxPage'
import { RfiSubmittalsPage } from '../features/rfi/RfiSubmittalsPage'
import { DailyReportsPage } from '../features/site/DailyReportsPage'
import { QualityPage } from '../features/quality/QualityPage'
import { SafetyPage } from '../features/safety/SafetyPage'
import { CustomersPage } from '../features/commercial/CustomersPage'
import { LeadsPage } from '../features/commercial/LeadsPage'
import { OpportunitiesPage } from '../features/commercial/OpportunitiesPage'
import { QuotationsPage } from '../features/commercial/QuotationsPage'
import { SalesContractsPage } from '../features/commercial/SalesContractsPage'
import { CompanySettingsPage } from '../features/settings/CompanySettingsPage'
import { navItems } from './navigation'

// Every visible navigation item resolves to a working screen. Capabilities that
// still lack a complete UI stay out of navigation until their route is ready.
const IMPLEMENTED_ROUTES: Record<string, RouteObject['element']> = {
  '/finanzas/contabilidad': <ReportsPage />,
  '/finanzas/tesoreria': <TreasuryPage />,
  '/finanzas/cuentas-por-pagar': <AccountsPayablePage />,
  '/finanzas/cuentas-por-cobrar': <AccountsReceivablePage />,
  '/finanzas/activos': <FixedAssetsPage />,
  '/proyectos': <ProjectsPage />,
  '/proyectos/wbs': <WBSPage />,
  '/proyectos/presupuestos': <BudgetPage />,
  '/proyectos/ordenes-de-cambio': <ChangeOrdersPage />,
  '/proyectos/avances': <ProgressPage />,
  '/proyectos/rfi-submittals': <RfiSubmittalsPage />,
  '/abastecimiento/solicitudes': <RequisitionsPage />,
  '/abastecimiento/ordenes-de-compra': <PurchaseOrdersPage />,
  '/abastecimiento/recepciones': <GoodsReceiptsPage />,
  '/abastecimiento/inventario': <InventoryPage />,
  '/abastecimiento/almacenes': <WarehousesPage />,
  '/abastecimiento/proveedores': <SuppliersPage />,
  '/abastecimiento/contratos': <SupplierContractsPage />,
  '/abastecimiento/comparativos': <BidComparisonPage />,
  '/recursos/personal': <WorkersPage />,
  '/recursos/cuadrillas': <CrewsPage />,
  '/recursos/tiempo': <TimeEntriesPage />,
  '/recursos/equipos': <EquipmentPage />,
  '/recursos/combustible': <EquipmentPage />,
  '/recursos/mantenimiento': <EquipmentPage />,
  '/control/documentos': <DocumentsPage />,
  '/control/evidencias': <DocumentsPage />,
  '/control/auditoria': <AuditLogPage />,
  '/control/configuracion': <CompanySettingsPage />,
  '/control/reportes': <ReportsPage />,
  '/inicio/aprobaciones': <ApprovalInboxPage />,
  '/proyectos/diario-de-obra': <DailyReportsPage />,
  '/proyectos/calidad': <QualityPage />,
  '/proyectos/seguridad': <SafetyPage />,
  '/comercial/leads': <LeadsPage />,
  '/comercial/oportunidades': <OpportunitiesPage />,
  '/comercial/clientes': <CustomersPage />,
  '/comercial/cotizaciones': <QuotationsPage />,
  '/comercial/contratos': <SalesContractsPage />,
  '/comercial/facturacion': <AccountsReceivablePage />,
  '/comercial/cobros': <AccountsReceivablePage />,
}

const applicationRoutes: RouteObject[] = navItems
  .filter((item) => item.path !== '/inicio')
  .map((item) => ({
    path: item.path.replace(/^\//, ''),
    element: IMPLEMENTED_ROUTES[item.path] ?? <Navigate to="/inicio" replace />,
  }))

export const routes: RouteObject[] = [
  { path: '/', element: <Navigate to="/inicio" replace /> },
  { path: '/login', element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [{ path: 'inicio', element: <HomePage /> }, ...applicationRoutes],
      },
    ],
  },
  { path: '*', element: <Navigate to="/inicio" replace /> },
]
