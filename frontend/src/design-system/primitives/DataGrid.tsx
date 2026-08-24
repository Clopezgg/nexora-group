import { useMemo, useState, type ReactNode } from 'react'
import type { TableColumn } from './Table'
import { EmptyState } from './States'

interface DataGridProps<T> {
  columns: TableColumn<T>[]
  rows: T[]
  getRowKey: (row: T) => string
  emptyMessage?: string
  defaultSortKey?: string
  sortValue?: (row: T, key: string) => string | number
}

/** Client-side sortable grid over an already-loaded row set. Sorting/pagination against a live backend belongs to each domain track's list endpoint (limit/offset + order_by), this only handles what's already on the page. */
export function DataGrid<T>({
  columns,
  rows,
  getRowKey,
  emptyMessage,
  defaultSortKey,
  sortValue,
}: DataGridProps<T>) {
  const [sortKey, setSortKey] = useState<string | undefined>(defaultSortKey)
  const [direction, setDirection] = useState<'asc' | 'desc'>('asc')

  const sortedRows = useMemo(() => {
    if (!sortKey || !sortValue) return rows
    const copy = [...rows]
    copy.sort((a, b) => {
      const av = sortValue(a, sortKey)
      const bv = sortValue(b, sortKey)
      if (av === bv) return 0
      const result = av > bv ? 1 : -1
      return direction === 'asc' ? result : -result
    })
    return copy
  }, [rows, sortKey, sortValue, direction])

  if (rows.length === 0) {
    return <EmptyState icon="🗒️" title={emptyMessage ?? 'Sin datos disponibles.'} />
  }

  const toggleSort = (key: string) => {
    if (!sortValue) return
    if (sortKey === key) {
      setDirection((current) => (current === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setDirection('asc')
    }
  }

  return (
    <table className="nx-table nx-data-grid">
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column.key}>
              {sortValue ? (
                <button
                  type="button"
                  className="nx-data-grid__sort"
                  onClick={() => toggleSort(column.key)}
                  aria-label={`Ordenar por ${column.header}`}
                >
                  {column.header}
                  {sortKey === column.key ? (
                    <span aria-hidden="true">{direction === 'asc' ? ' ▲' : ' ▼'}</span>
                  ) : null}
                </button>
              ) : (
                column.header
              )}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sortedRows.map((row) => (
          <tr key={getRowKey(row)}>
            {columns.map((column) => (
              <td key={column.key}>{column.render(row)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

interface FilterBarProps {
  children: ReactNode
  onClear?: () => void
}

export function FilterBar({ children, onClear }: FilterBarProps) {
  return (
    <div className="nx-filter-bar" role="search">
      <div className="nx-filter-bar__controls">{children}</div>
      {onClear ? (
        <button type="button" className="nx-filter-bar__clear" onClick={onClear}>
          Limpiar filtros
        </button>
      ) : null}
    </div>
  )
}
