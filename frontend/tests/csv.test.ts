import { describe, it, expect } from 'vitest'
import { toCsv } from '../src/utils/csv'

describe('toCsv', () => {
  it('produces a header row and one row per input record', () => {
    const csv = toCsv(
      [{ code: '1000', name: 'Caja', debit: '100.00' }],
      [
        { key: 'code', label: 'Código' },
        { key: 'name', label: 'Cuenta' },
        { key: 'debit', label: 'Débito' },
      ],
    )
    expect(csv).toBe('"Código","Cuenta","Débito"\n"1000","Caja","100.00"')
  })

  it('escapes embedded double quotes and handles multiple rows', () => {
    const csv = toCsv(
      [
        { name: 'Torre "Norte"', total: '1' },
        { name: 'Torre Sur', total: '2' },
      ],
      [
        { key: 'name', label: 'Nombre' },
        { key: 'total', label: 'Total' },
      ],
    )
    expect(csv).toBe('"Nombre","Total"\n"Torre ""Norte""","1"\n"Torre Sur","2"')
  })

  it('renders null/undefined values as an empty quoted cell', () => {
    const csv = toCsv(
      [{ name: 'Sin dato', note: null as unknown as string }],
      [
        { key: 'name', label: 'Nombre' },
        { key: 'note', label: 'Nota' },
      ],
    )
    expect(csv).toBe('"Nombre","Nota"\n"Sin dato",""')
  })
})
