import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Table, type TableColumn } from '../src/design-system'

interface Row {
  id: string
  proveedor: string
  monto: string
}

const columns: TableColumn<Row>[] = [
  { key: 'proveedor', header: 'Proveedor', render: (r) => r.proveedor },
  { key: 'monto', header: 'Monto', numeric: true, render: (r) => r.monto },
]

describe('Table responsive (record cards en móvil)', () => {
  it('marca cada celda con data-label y la clase responsive para el apilado móvil (§22/§23)', () => {
    render(
      <Table
        columns={columns}
        rows={[{ id: '1', proveedor: 'Ferretería El Clavo', monto: 'L 1,000.00' }]}
        getRowKey={(r) => r.id}
      />,
    )

    const table = screen.getByRole('table')
    expect(table).toHaveClass('nx-table--responsive')

    const montoCell = screen.getByText('L 1,000.00').closest('td')
    expect(montoCell).toHaveAttribute('data-label', 'Monto')
    expect(montoCell).toHaveClass('nx-table__cell--numeric')
  })
})
