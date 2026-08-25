import { Tabs } from '../../design-system'
import { BudgetVsActualPage } from './BudgetVsActualPage'
import { TrialBalancePage } from './TrialBalancePage'

/** `/control/reportes` ya existía como entrada reservada ("Reportes") en
 * navigation.ts -- no se inventó una ruta nueva, mismo criterio que
 * `/control/auditoria` (Track G) e `/inicio/aprobaciones` usaron antes.
 * Un único slot de navegación aloja los dos reportes de esta fase
 * (NXR-REQ-0093) como tabs, mismo patrón que EquipmentPage ya usa para
 * Equipos/Combustible/Mantenimiento bajo distintas entradas de nav. */
export function ReportsPage() {
  return (
    <Tabs
      items={[
        { key: 'balance-comprobacion', label: 'Balance de Comprobación', content: <TrialBalancePage /> },
        { key: 'presupuesto-vs-real', label: 'Presupuesto vs. Real', content: <BudgetVsActualPage /> },
      ]}
    />
  )
}
