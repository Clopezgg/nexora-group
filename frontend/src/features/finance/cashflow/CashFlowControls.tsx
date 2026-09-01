import { Select } from '../../../design-system'
import './cashflow.css'
import type {
  CashFlowGranularityOption,
  CashFlowMode,
  CashFlowRange,
} from './useCashFlowSeries'

export interface CashFlowControlsProps {
  mode: CashFlowMode
  onModeChange: (mode: CashFlowMode) => void
  range: CashFlowRange
  onRangeChange: (range: CashFlowRange) => void
  granularity: CashFlowGranularityOption
  onGranularityChange: (granularity: CashFlowGranularityOption) => void
  /** Home uses a tighter layout; the full page shows the descriptive select label. */
  compact?: boolean
}

const RANGES: CashFlowRange[] = ['1M', '3M', '6M', '12M']

/**
 * Controles compartidos: REALIZADO | PROYECTADO, rango 1M/3M/6M/12M y
 * agrupación Auto/Día/Semana/Mes (ORDEN MAESTRA §5/§10). La agrupación solo
 * aplica al modo REALIZADO.
 */
export function CashFlowControls({
  mode,
  onModeChange,
  range,
  onRangeChange,
  granularity,
  onGranularityChange,
  compact = false,
}: CashFlowControlsProps) {
  return (
    <div className="nx-cashflow-controls">
      <div className="nx-segmented" role="tablist" aria-label="Modo de flujo de caja">
        {(['REALIZADO', 'PROYECTADO'] as const).map((option) => (
          <button
            key={option}
            type="button"
            role="tab"
            aria-selected={mode === option}
            className={`nx-segmented__option${mode === option ? ' nx-segmented__option--active' : ''}`}
            onClick={() => onModeChange(option)}
          >
            {option === 'REALIZADO' ? 'Realizado' : 'Proyectado'}
          </button>
        ))}
      </div>

      {mode === 'REALIZADO' ? (
        <>
          <div className="nx-segmented" role="group" aria-label="Rango de fechas">
            {RANGES.map((r) => (
              <button
                key={r}
                type="button"
                className={`nx-segmented__option${range === r ? ' nx-segmented__option--active' : ''}`}
                onClick={() => onRangeChange(r)}
              >
                {r}
              </button>
            ))}
          </div>
          <Select
            label={compact ? 'Agrupar' : 'Agrupación'}
            value={granularity}
            onChange={(e) => onGranularityChange(e.target.value as CashFlowGranularityOption)}
          >
            <option value="auto">Auto</option>
            <option value="day">Día</option>
            <option value="week">Semana</option>
            <option value="month">Mes</option>
          </Select>
        </>
      ) : null}
    </div>
  )
}
