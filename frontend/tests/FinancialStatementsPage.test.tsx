import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './testUtils'

function stubFetch(overrides: {
  companies?: unknown[]
  balanceSheet?: unknown
  incomeStatement?: unknown
  cashFlow?: unknown
  supplierPerformance?: unknown
}) {
  const companies = overrides.companies ?? [
    { id: 'c1', name: 'Constructora Nexora', code: null, legalName: null, functionalCurrencyCode: 'HNL' },
  ]
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((input: RequestInfo | URL) => {
      const url = String(input)
      if (url.includes('/auth/me')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ id: 'u1', email: 'admin@nexora.group', fullName: 'Admin', roles: ['Administrator'] }),
        } as Response)
      }
      if (url.includes('/master-data/companies')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => companies } as Response)
      }
      if (url.includes('/reports/trial-balance')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => ({ rows: [], totalDebit: '0', totalCredit: '0' }) } as Response)
      }
      if (url.includes('/reports/balance-sheet')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => overrides.balanceSheet ?? {} } as Response)
      }
      if (url.includes('/reports/income-statement')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => overrides.incomeStatement ?? {} } as Response)
      }
      if (url.includes('/reports/cash-flow')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => overrides.cashFlow ?? {} } as Response)
      }
      if (url.includes('/reports/supplier-performance')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => overrides.supplierPerformance ?? [] } as Response)
      }
      if (url.includes('/context')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ activeProjectId: null, activeProjectName: null }),
        } as Response)
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) } as Response)
    }),
  )
}

describe('BalanceSheetPage', () => {
  it('renders the balance-sheet equation from the real API response', async () => {
    stubFetch({
      balanceSheet: {
        assets: [{ accountId: 'a1', accountCode: '1000', accountName: 'Caja', accountType: 'ASSET', balance: '150.00' }],
        liabilities: [],
        equity: [{ accountId: 'a2', accountCode: '3000', accountName: 'Capital', accountType: 'EQUITY', balance: '100.00' }],
        totalAssets: '150.00',
        totalLiabilities: '0.00',
        totalEquity: '100.00',
        currentEarnings: '50.00',
        totalEquityIncludingEarnings: '150.00',
        totalLiabilitiesAndEquity: '150.00',
        equationDelta: '0.00',
      },
    })

    render(renderApp('/control/reportes'))
    await userEvent.click(await screen.findByRole('tab', { name: /balance general/i }))

    expect(await screen.findByText('Caja')).toBeInTheDocument()
    expect(screen.getByText('Capital')).toBeInTheDocument()
    expect(screen.getByText(/activos: L 150\.00/i)).toBeInTheDocument()
    expect(screen.getByText(/pasivo \+ patrimonio: L 150\.00/i)).toBeInTheDocument()
  })

  it('shows an honest empty state when there are no companies yet', async () => {
    stubFetch({ companies: [] })

    render(renderApp('/control/reportes'))
    await userEvent.click(await screen.findByRole('tab', { name: /balance general/i }))

    expect(await screen.findByText(/configura una compañía primero/i)).toBeInTheDocument()
  })
})

describe('IncomeStatementPage', () => {
  it('renders revenue, expenses and net income from the real API response', async () => {
    stubFetch({
      incomeStatement: {
        revenue: [{ accountId: 'a1', accountCode: '4000', accountName: 'Ventas de Servicios', accountType: 'REVENUE', balance: '100.00' }],
        expenses: [{ accountId: 'a2', accountCode: '5000', accountName: 'Gastos Operativos', accountType: 'EXPENSE', balance: '25.00' }],
        totalRevenue: '100.00',
        totalExpenses: '25.00',
        netIncome: '75.00',
      },
    })

    render(renderApp('/control/reportes'))
    await userEvent.click(await screen.findByRole('tab', { name: /estado de resultados/i }))

    expect(await screen.findByText('Ventas de Servicios')).toBeInTheDocument()
    expect(screen.getByText('Gastos Operativos')).toBeInTheDocument()
    expect(screen.getByText(/utilidad neta: L 75\.00/i)).toBeInTheDocument()
  })

  it('disables the CSV export button when there are no rows', async () => {
    stubFetch({
      incomeStatement: {
        revenue: [],
        expenses: [],
        totalRevenue: '0.00',
        totalExpenses: '0.00',
        netIncome: '0.00',
      },
    })

    render(renderApp('/control/reportes'))
    await userEvent.click(await screen.findByRole('tab', { name: /estado de resultados/i }))

    expect(await screen.findByRole('button', { name: /exportar csv/i })).toBeDisabled()
  })
})

describe('CashFlowPage', () => {
  it('renders classified activities, the unclassified bucket and the net cash change from the real API response', async () => {
    stubFetch({
      cashFlow: {
        operating: [{ accountId: 'a1', accountCode: '5100', accountName: 'Gastos administrativos', accountType: 'OPERATING', balance: '-300.00' }],
        investing: [],
        financing: [{ accountId: 'a2', accountCode: '3100', accountName: 'Aportes de socios', accountType: 'FINANCING', balance: '5000.00' }],
        unclassified: [{ accountId: 'a3', accountCode: '2100', accountName: 'CxP sin clasificar', accountType: 'UNCLASSIFIED', balance: '-100.00' }],
        totalOperating: '-300.00',
        totalInvesting: '0.00',
        totalFinancing: '5000.00',
        totalUnclassified: '-100.00',
        netChangeInCash: '4600.00',
      },
    })

    render(renderApp('/control/reportes'))
    await userEvent.click(await screen.findByRole('tab', { name: /flujo de efectivo/i }))

    expect(await screen.findByText('Aportes de socios')).toBeInTheDocument()
    expect(screen.getByText('Gastos administrativos')).toBeInTheDocument()
    expect(screen.getByText('CxP sin clasificar')).toBeInTheDocument()
    expect(screen.getByText(/cambio neto en efectivo: L 4,600\.00/i)).toBeInTheDocument()
  })

  it('hides the unclassified card when every account is classified', async () => {
    stubFetch({
      cashFlow: {
        operating: [],
        investing: [],
        financing: [{ accountId: 'a2', accountCode: '3100', accountName: 'Aportes de socios', accountType: 'FINANCING', balance: '1000.00' }],
        unclassified: [],
        totalOperating: '0.00',
        totalInvesting: '0.00',
        totalFinancing: '1000.00',
        totalUnclassified: '0.00',
        netChangeInCash: '1000.00',
      },
    })

    render(renderApp('/control/reportes'))
    await userEvent.click(await screen.findByRole('tab', { name: /flujo de efectivo/i }))

    expect(await screen.findByText('Aportes de socios')).toBeInTheDocument()
    expect(screen.queryByText(/sin clasificar/i)).not.toBeInTheDocument()
  })
})

describe('SupplierPerformancePage', () => {
  it('renders real per-supplier metrics with sample size from the real API response', async () => {
    stubFetch({
      supplierPerformance: [
        {
          supplierId: 's1', supplierLegalName: 'Buen Proveedor S.A.', purchaseOrderCount: 2,
          onTimeDeliveryRate: '100.00', onTimeDeliverySampleSize: 2,
          threeWayMatchCleanRate: '100.00', threeWayMatchSampleSize: 2,
          priceVariancePct: '0.00', priceVarianceSampleSize: 1,
        },
        {
          supplierId: 's2', supplierLegalName: 'Proveedor Nuevo S.A.', purchaseOrderCount: 0,
          onTimeDeliveryRate: null, onTimeDeliverySampleSize: 0,
          threeWayMatchCleanRate: null, threeWayMatchSampleSize: 0,
          priceVariancePct: null, priceVarianceSampleSize: 0,
        },
      ],
    })

    render(renderApp('/control/reportes'))
    await userEvent.click(await screen.findByRole('tab', { name: /desempeño de proveedores/i }))

    expect(await screen.findByText('Buen Proveedor S.A.')).toBeInTheDocument()
    expect(screen.getAllByText(/100\.00% \(n=2\)/).length).toBeGreaterThan(0)
    expect(screen.getByText('Proveedor Nuevo S.A.')).toBeInTheDocument()
    // honest "no data" instead of a fabricated 0%/100% for the new supplier
    expect(screen.getAllByText(/sin datos suficientes \(n=0\)/i).length).toBeGreaterThan(0)
  })
})
