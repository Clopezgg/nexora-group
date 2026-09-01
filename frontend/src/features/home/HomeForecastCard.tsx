import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, EmptyState, LoadingState } from '../../design-system'
import {
  CashFlowChart,
  CashFlowControls,
  CashFlowSummary,
  useCashFlowSeries,
  type CashFlowGranularityOption,
  type CashFlowMode,
  type CashFlowRange,
} from '../finance/cashflow'

/**
 * Flujo de caja en el Home (ORDEN MAESTRA §5/§6/§7).
 *
 * Usa la MISMA arquitectura moderna que la página completa
 * (`useCashFlowSeries` + `cashFlowActualService.series()`): rangos reales
 * 1M/3M/6M/12M, agrupación Auto/Día/Semana/Mes y etiquetas de calendario.
 * NUNCA "S1 S2 S3 … S13" como lenguaje principal — ni en REALIZADO ni en
 * PROYECTADO.
 */
export function HomeForecastCard({ companyId }: { companyId: string }) {
  const [mode, setMode] = useState<CashFlowMode>('REALIZADO')
  const [range, setRange] = useState<CashFlowRange>('3M')
  const [granularity, setGranularity] = useState<CashFlowGranularityOption>('auto')

  const { rows, summary, hasMovement, isLoading, isError, refetch } = useCashFlowSeries({
    companyId,
    mode,
    range,
    granularity,
  })
  const currency = summary?.currencyCode ?? 'HNL'

  return (
    <Card title="Flujo de caja">
      <CashFlowControls
        mode={mode}
        onModeChange={setMode}
        range={range}
        onRangeChange={setRange}
        granularity={granularity}
        onGranularityChange={setGranularity}
        compact
      />

      {isLoading ? (
        <LoadingState label="Cargando flujo de caja…" />
      ) : isError ? (
        <div className="nx-home__forecast-empty">
          <EmptyState icon="chart" title="No se pudo cargar el flujo de caja" />
          <button type="button" className="nx-linkbutton" onClick={refetch}>
            Reintentar
          </button>
        </div>
      ) : !hasMovement ? (
        <div className="nx-home__forecast-empty">
          <EmptyState
            icon="chart"
            title={
              mode === 'REALIZADO'
                ? 'Sin movimientos de tesorería en el rango seleccionado'
                : 'Aún no hay compromisos AP/AR suficientes para proyectar'
            }
          />
          <Link to="/finanzas/flujo-13-semanas">Abrir Flujo de caja →</Link>
        </div>
      ) : (
        <>
          {summary ? <CashFlowSummary summary={summary} /> : null}
          <CashFlowChart rows={rows} currency={currency} height={220} />
          <Link to="/finanzas/flujo-13-semanas">Ver flujo de caja completo →</Link>
        </>
      )}
    </Card>
  )
}
