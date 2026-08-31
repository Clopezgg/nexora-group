import { useState, type ReactNode } from 'react'
import { Tabs } from '../../design-system'
import { BalanceSheetPage } from './BalanceSheetPage'
import { BudgetVsActualPage } from './BudgetVsActualPage'
import { CashFlowPage } from './CashFlowPage'
import { GeneralLedgerPage } from './GeneralLedgerPage'
import { IncomeStatementPage } from './IncomeStatementPage'
import { SupplierPerformancePage } from './SupplierPerformancePage'
import { TrialBalancePage } from './TrialBalancePage'

/** Financial Reporting Center (orden maestra FINAL, Phase 9). Un único slot
 * de navegación aloja los reportes como tabs. Drill-down real: del Balance de
 * Comprobación → Libro Mayor filtrado por cuenta → Transaction Inspector del
 * documento. */
export function ReportsPage({ accountCatalog }: { accountCatalog?: ReactNode }) {
  const [tab, setTab] = useState(accountCatalog ? 'catalogo-cuentas' : 'balance-comprobacion')
  const [ledgerAccountId, setLedgerAccountId] = useState<string | null>(null)
  const [ledgerAccountLabel, setLedgerAccountLabel] = useState<string | null>(null)

  const drillToLedger = (accountId: string, label: string) => {
    setLedgerAccountId(accountId)
    setLedgerAccountLabel(label)
    setTab('libro-mayor')
  }

  return (
    <Tabs
      activeKey={tab}
      onChange={setTab}
      items={[
        ...(accountCatalog
          ? [{ key: 'catalogo-cuentas', label: 'Catálogo de cuentas', content: accountCatalog }]
          : []),
        {
          key: 'balance-comprobacion',
          label: 'Balance de Comprobación',
          content: <TrialBalancePage onDrillToLedger={drillToLedger} />,
        },
        {
          key: 'presupuesto-vs-real',
          label: 'Presupuesto vs. Real',
          content: <BudgetVsActualPage />,
        },
        {
          key: 'libro-mayor',
          label: 'Libro Mayor',
          content: (
            <GeneralLedgerPage
              accountId={ledgerAccountId}
              accountLabel={ledgerAccountLabel}
              onClearAccountFilter={() => {
                setLedgerAccountId(null)
                setLedgerAccountLabel(null)
              }}
            />
          ),
        },
        { key: 'balance-general', label: 'Balance General', content: <BalanceSheetPage /> },
        {
          key: 'estado-resultados',
          label: 'Estado de Resultados',
          content: <IncomeStatementPage />,
        },
        { key: 'flujo-de-efectivo', label: 'Flujo de Efectivo', content: <CashFlowPage /> },
        {
          key: 'desempeno-proveedores',
          label: 'Desempeño de Proveedores',
          content: <SupplierPerformancePage />,
        },
      ]}
    />
  )
}
