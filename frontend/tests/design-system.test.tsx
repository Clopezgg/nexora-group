import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import {
  CommandPalette,
  Combobox,
  Input,
  MoneyInput,
  Select,
  StatCard,
  Tabs,
  EntitySelector,
} from '../src/design-system'

describe('Form controls', () => {
  it('associates generated ids with Input and Select labels', () => {
    render(
      <>
        <Input label="Nombre" />
        <Select label="Moneda">
          <option value="HNL">HNL</option>
        </Select>
      </>,
    )

    expect(screen.getByLabelText('Nombre')).toHaveProperty('type', 'text')
    expect(screen.getByLabelText('Moneda')).toHaveValue('HNL')
  })
})

describe('CommandPalette', () => {
  it('opens on Cmd/Ctrl+K and navigates to the selected route', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/inicio']}>
        <CommandPalette
          items={[{ id: '/abastecimiento/rfq', label: 'RFQ', group: 'Abastecimiento', path: '/abastecimiento/rfq' }]}
        />
      </MemoryRouter>,
    )

    expect(screen.queryByPlaceholderText(/ir a…/i)).not.toBeInTheDocument()

    await user.keyboard('{Meta>}k{/Meta}')
    expect(await screen.findByPlaceholderText(/ir a…/i)).toBeInTheDocument()

    await user.click(screen.getByRole('option', { name: /rfq/i }))
    expect(screen.queryByPlaceholderText(/ir a…/i)).not.toBeInTheDocument()
  })
})

describe('MoneyInput', () => {
  it('rejects non-numeric input and reports the parsed value to onChange', async () => {
    function Harness() {
      const [value, setValue] = useState<number | null>(null)
      return (
        <div>
          <MoneyInput label="Monto" value={value} onChange={setValue} />
          <span data-testid="value">{value ?? 'null'}</span>
        </div>
      )
    }
    const user = userEvent.setup()
    render(<Harness />)

    const input = screen.getByLabelText('Monto')
    await user.type(input, '12.5')
    expect(screen.getByTestId('value').textContent).toBe('12.5')

    await user.type(input, 'abc')
    expect(screen.getByTestId('value').textContent).toBe('12.5')
  })
})

describe('Combobox', () => {
  it('filters options as the user types and calls onChange on selection', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <Combobox
        label="Cuenta"
        options={[
          { value: '1', label: 'Caja General' },
          { value: '2', label: 'Banco Central' },
        ]}
        value={null}
        onChange={onChange}
      />,
    )

    const input = screen.getByLabelText('Cuenta')
    await user.click(input)
    await user.type(input, 'banco')
    await user.click(screen.getByRole('option', { name: /banco central/i }))

    expect(onChange).toHaveBeenCalledWith('2')
  })
})

describe('EntitySelector', () => {
  it('renders an honest empty state when no options are loaded yet', () => {
    render(
      <EntitySelector
        label="Proveedor"
        options={[]}
        value={null}
        onChange={() => {}}
        emptyLabel="Aún no hay proveedores registrados."
      />,
    )
    expect(screen.getByText('Aún no hay proveedores registrados.')).toBeInTheDocument()
  })
})

describe('StatCard', () => {
  it('renders label and value', () => {
    render(<StatCard label="Proyectos activos" value={4} />)
    expect(screen.getByText('Proyectos activos')).toBeInTheDocument()
    expect(screen.getByText('4')).toBeInTheDocument()
  })
})

describe('Tabs', () => {
  it('switches panels on tab click', async () => {
    const user = userEvent.setup()
    render(
      <Tabs
        items={[
          { key: 'a', label: 'Resumen', content: <p>Contenido A</p> },
          { key: 'b', label: 'Detalle', content: <p>Contenido B</p> },
        ]}
      />,
    )
    expect(screen.getByText('Contenido A')).toBeInTheDocument()
    await user.click(screen.getByRole('tab', { name: 'Detalle' }))
    expect(screen.getByText('Contenido B')).toBeInTheDocument()
  })
})
