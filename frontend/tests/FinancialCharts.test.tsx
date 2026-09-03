import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import FinancialCharts from '../src/features/home/FinancialCharts'

describe('FinancialCharts', () => {
  it('treats Decimal-safe string amounts from the API as zero, not as truthy noise', () => {
    // El backend serializa dinero como Decimal -> string JSON ("0.00"), no
    // como float. Con montos "0.00" el gráfico de gastos por alcance debe
    // seguir mostrando el estado vacío real, no una barra fantasma de "0".
    render(
      <FinancialCharts
        cashFlow={[{ period: '2026-08', income: '0.00', expense: '0.00' }]}
        expensesByScope={[{ scope: 'PROJECT', amount: '0.00' }]}
        currency="HNL"
      />,
    )

    expect(screen.getByText('Sin gastos registrados por alcance.')).toBeInTheDocument()
    expect(screen.getByText('Sin movimientos en este período.')).toBeInTheDocument()
  })

  it('renders real non-zero string amounts as actual chart data', () => {
    render(
      <FinancialCharts
        cashFlow={[{ period: '2026-08', income: '1250.50', expense: '0.00' }]}
        expensesByScope={[{ scope: 'PROJECT', amount: '340.00' }]}
        currency="HNL"
      />,
    )

    expect(screen.queryByText('Sin gastos registrados por alcance.')).not.toBeInTheDocument()
    expect(screen.queryByText('Sin movimientos en este período.')).not.toBeInTheDocument()
  })
})
