import type { ReactNode } from 'react'

export interface TableColumn<T> {
  key: string
  header: string
  render: (row: T) => ReactNode
  /** Alinea la celda; los importes financieros van a la derecha (§29). */
  align?: 'left' | 'right'
  /** Marca la columna como numérica: activa `tabular-nums` y alinea a la
   * derecha salvo que `align` diga lo contrario. Obligatorio en débito,
   * crédito, monto, saldo, presupuesto, costo y precio. */
  numeric?: boolean
}

interface TableProps<T> {
  columns: TableColumn<T>[]
  rows: T[]
  getRowKey: (row: T) => string
  emptyMessage?: string
}

function cellClass<T>(column: TableColumn<T>): string | undefined {
  const align = column.align ?? (column.numeric ? 'right' : undefined)
  return [align === 'right' ? 'nx-table__cell--right' : '', column.numeric ? 'nx-table__cell--numeric' : '']
    .filter(Boolean)
    .join(' ') || undefined
}

export function Table<T>({ columns, rows, getRowKey, emptyMessage }: TableProps<T>) {
  if (rows.length === 0) {
    return <p className="nx-field__label">{emptyMessage ?? 'Sin datos disponibles.'}</p>
  }
  return (
    // En escritorio: tabla densa dentro de su propio contenedor con scroll
    // horizontal (§4/§105). En móvil (`@media`): cada fila se apila como
    // "record card" con etiqueta/valor por columna (§22/§23) — se evita
    // comprimir 8 columnas. El `data-label` alimenta el `::before` en CSS.
    <div className="nx-table-scroll" tabIndex={0}>
      <table className="nx-table nx-table--responsive">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column.key} className={cellClass(column)}>
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={getRowKey(row)}>
              {columns.map((column) => (
                <td key={column.key} className={cellClass(column)} data-label={column.header}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
