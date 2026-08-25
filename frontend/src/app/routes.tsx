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
import { FixedAssetsPage } from '../features/assets/FixedAssetsPage'
import { EquipmentPage } from '../features/equipment/EquipmentPage'
import { WorkersPage } from '../features/workforce/WorkersPage'
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

// Workforce/Time; Documents/Evidence, RFI/Submittals, and Daily Site
// Reports/Quality/Safety are all implemented too -- ver
// docs/DOCUMENTS_EVIDENCE.md, docs/PROGRESS.md, and
// docs/REQUIREMENTS_TRACEABILITY.md NXR-REQ-0077-0086) and Track E
// (Commercial -- Lead/Opportunity/Customer/Quotation/SalesContract;
// Facturación y Cobros del menú Comercial se resuelven desde las páginas de
// AR ya existentes en Finanzas -- Track E nunca duplica esa UI, ver
// docs/ACCOUNTING.md) implementan estas rutas; el resto de navItems sigue
// como PlaceholderPage hasta que su track dueño aterrice. Workers/TimeEntry
// viven en las rutas ya reservadas para ellos en navigation.ts
// (`/recursos/personal`, `/recursos/tiempo`) -- no existe un ítem de
// navegación `/recursos/mano-de-obra`, así que no se inventa uno nuevo
// (DEFERRED-FINAL-008). `/proyectos/seguridad` es un ítem de navegación
// nuevo agregado por Task 3 (Safety, NXR-REQ-0084) -- no existía una
// entrada reservada para Seguridad en navigation.ts, mismo criterio que
// RFI/Submittals usó para `/proyectos/rfi-submittals`. `/control/auditoria`
// (Track G, NXR-REQ-0090) ya existía como entrada reservada en
// navigation.ts ("Auditoría") -- no se inventó una sección Plataforma
// nueva, se implementó la ruta ya reservada. `/inicio/aprobaciones` (Track
// G, NXR-REQ-0088, Approval Inbox) mismo criterio: ya existía como entrada
// reservada ("Aprobaciones" bajo el grupo Inicio) en navigation.ts -- no se
// inventó `/plataforma/aprobaciones` ni ninguna otra ruta nueva.
// `/control/configuracion` (Task 3, NXR-REQ-0095, Settings) mismo criterio:
// ya existía como entrada reservada ("Configuración") en navigation.ts --
// no se inventó una sección nueva, se implementó la ruta ya reservada.
// `/control/reportes` (Task 2 de este plan, NXR-REQ-0093/0094) mismo
// criterio: ya existía como entrada reservada ("Reportes") en
// navigation.ts -- no se inventó una ruta nueva. Los dos reportes de esta
// fase (Trial Balance + Budget vs Actual) viven bajo ese único slot como
// tabs (ReportsPage), mismo patrón que EquipmentPage ya usa para alojar
// varias sub-vistas bajo distintas entradas de nav.
const IMPLEMENTED_ROUTES: Record<string, RouteObject['element']> = {
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
  '/recursos/personal': <WorkersPage />,
  '/recursos/tiempo': <TimeEntriesPage />,
  '/recursos/equipos': <EquipmentPage />,
  '/recursos/combustible': <EquipmentPage />,
  '/recursos/mantenimiento': <EquipmentPage />,
  '/control/documentos': <DocumentsPage />,
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
