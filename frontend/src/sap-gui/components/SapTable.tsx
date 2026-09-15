/**
 * NEXORA SAP GUI Classic — Table Primitive
 * 
 * Tabla estilo SAP GUI Classic (Table Control / Grid).
 * - Filas compactas (26px)
 * - Header compacto
 * - Rejilla visible
 * - Selección de fila
 * - Scroll horizontal
 * - Alineación numérica correcta
 * - Navegación por teclado
 */

import { forwardRef, type HTMLAttributes, type ReactNode, useRef, useEffect, useState } from 'react';
import './SapTable.css';

export interface SapTableColumn<T> {
  key: string;
  header: string;
  render: (row: T, index: number) => ReactNode;
  align?: 'left' | 'right' | 'center';
  width?: string;
  minWidth?: string;
  sortable?: boolean;
}

export interface SapTableProps<T> extends HTMLAttributes<HTMLTableElement> {
  columns: SapTableColumn<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  onRowClick?: (row: T, index: number) => void;
  onRowDoubleClick?: (row: T, index: number) => void;
  selectedKey?: string;
  onSelectionChange?: (key: string) => void;
  emptyMessage?: string;
  responsive?: boolean;
  dense?: boolean;
  striped?: boolean;
}

export const SapTable = forwardRef<HTMLTableElement, SapTableProps<unknown>>(
  ({ 
    columns, 
    rows, 
    getRowKey, 
    onRowClick, 
    onRowDoubleClick, 
    selectedKey, 
    onSelectionChange,
    emptyMessage = 'Sin datos.',
    responsive = false,
    dense = false,
    striped = false,
    className = '',
    ...props 
  }, ref) => {
    const [focusedRowIndex, setFocusedRowIndex] = useState(-1);
    const tableRef = useRef<HTMLTableElement>(null);
    
    useEffect(() => {
      if (tableRef.current && ref) {
        if ('current' in ref) {
          ref.current = tableRef.current;
        } else if (typeof ref === 'function') {
          ref(tableRef.current);
        }
      }
    }, [ref]);

    const handleKeyDown = (event: React.KeyboardEvent) => {
      if (rows.length === 0) return;
      
      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          setFocusedRowIndex(prev => Math.min(prev + 1, rows.length - 1));
          break;
        case 'ArrowUp':
          event.preventDefault();
          setFocusedRowIndex(prev => Math.max(prev - 1, 0));
          break;
        case 'Home':
          event.preventDefault();
          setFocusedRowIndex(0);
          break;
        case 'End':
          event.preventDefault();
          setFocusedRowIndex(rows.length - 1);
          break;
        case 'Enter':
        case ' ':
          if (focusedRowIndex >= 0 && onRowClick) {
            event.preventDefault();
            onRowClick(rows[focusedRowIndex], focusedRowIndex);
          }
          break;
        case 'Escape':
          setFocusedRowIndex(-1);
          break;
      }
    };

    if (rows.length === 0) {
      return (
        <div className="nx-sap-table-empty" role="status">
          {emptyMessage}
        </div>
      );
    }

    return (
      <div className={`nx-sap-table-wrapper ${responsive ? 'nx-responsive' : ''} ${dense ? 'nx-dense' : ''} ${striped ? 'nx-striped' : ''} ${className}`} 
           onKeyDown={handleKeyDown}
           tabIndex={0}
           role="grid"
           aria-label={props['aria-label']}>
        <div className="nx-sap-table-scroll">
          <table ref={tableRef} className="nx-sap-table" {...props}>
            <colgroup>
              {columns.map((col) => (
                <col key={col.key} style={{ width: col.width, minWidth: col.minWidth }} />
              ))}
            </colgroup>
            <thead className="nx-sap-table__thead">
              <tr role="row">
                {columns.map((col) => (
                  <th 
                    key={col.key}
                    scope="col"
                    className="nx-sap-table__th"
                    style={{ 
                      textAlign: col.align || 'left',
                      width: col.width,
                      minWidth: col.minWidth,
                    }}
                    aria-sort="none"
                  >
                    <span className="nx-sap-table__th-content">{col.header}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="nx-sap-table__tbody">
              {rows.map((row, rowIndex) => {
                const rowKey = getRowKey(row);
                const isSelected = selectedKey === rowKey;
                const isFocused = focusedRowIndex === rowIndex;
                
                return (
                  <tr
                    key={rowKey}
                    role="row"
                    className={`nx-sap-table__tr ${isSelected ? 'nx-selected' : ''} ${isFocused ? 'nx-focused' : ''} ${striped && rowIndex % 2 === 1 ? 'nx-striped-row' : ''}`}
                    tabIndex={isFocused ? 0 : -1}
                    aria-selected={isSelected}
                    aria-current={isFocused ? 'true' : undefined}
                    onClick={() => {
                      setFocusedRowIndex(rowIndex);
                      if (onSelectionChange) onSelectionChange(rowKey);
                      if (onRowClick) onRowClick(row, rowIndex);
                    }}
                    onDoubleClick={() => {
                      if (onRowDoubleClick) onRowDoubleClick(row, rowIndex);
                    }}
                    onFocus={() => setFocusedRowIndex(rowIndex)}
                  >
                    {columns.map((col) => (
                      <td 
                        key={col.key}
                        role="gridcell"
                        className="nx-sap-table__td"
                        style={{ 
                          textAlign: col.align || 'left',
                          width: col.width,
                          minWidth: col.minWidth,
                        }}
                      >
                        <div className="nx-sap-table__td-content">
                          {col.render(row, rowIndex)}
                        </div>
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }
);

SapTable.displayName = 'SapTable';

/**
 * Columna de acciones estándar
 */
// eslint-disable-next-line react-refresh/only-export-components
export function createActionColumn<T>(
  actions: Array<{
    key: string;
    label: string;
    icon?: ReactNode;
    onClick: (row: T, event: React.MouseEvent) => void;
    disabled?: (row: T) => boolean;
    hidden?: (row: T) => boolean;
  }>
): SapTableColumn<T> {
  return {
    key: 'actions',
    header: 'Acción',
    align: 'center',
    width: '120px',
    render: (row: T) => (
      <div className="nx-sap-table__actions">
        {actions.map((action) => {
          if (action.hidden?.(row)) return null;
          const disabled = action.disabled?.(row);
          return (
            <button
              key={action.key}
              type="button"
              className="nx-sap-table__action-btn"
              disabled={disabled}
              onClick={(e) => { e.stopPropagation(); action.onClick(row, e); }}
              title={action.label}
              aria-label={action.label}
              tabIndex={-1}
            >
              {action.icon}
              <span className="nx-sap-table__action-text">{action.label}</span>
            </button>
          );
        })}
      </div>
    ),
  };
}