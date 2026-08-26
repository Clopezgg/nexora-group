import { useQuery } from '@tanstack/react-query'
import { Card, EmptyState, ErrorState, LoadingState, Table, type TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { reportingService } from '../../services/reportingService'
import type { SupplierPerformanceRow } from '../../types/reporting'

const NO_DATA = 'Sin datos suficientes'

function formatRate(rate: string | null, sampleSize: number): string {
  if (rate === null) return `${NO_DATA} (n=${sampleSize})`
  return `${rate}% (n=${sampleSize})`
}

const COLUMNS: TableColumn<SupplierPerformanceRow>[] = [
  { key: 'supplierLegalName', header: 'Proveedor', render: (row) => row.supplierLegalName },
  { key: 'purchaseOrderCount', header: 'Órdenes de compra', render: (row) => String(row.purchaseOrderCount) },
  {
    key: 'onTimeDeliveryRate',
    header: 'Entrega a tiempo',
    render: (row) => formatRate(row.onTimeDeliveryRate, row.onTimeDeliverySampleSize),
  },
  {
    key: 'threeWayMatchCleanRate',
    header: 'Three-way match sin excepción',
    render: (row) => formatRate(row.threeWayMatchCleanRate, row.threeWayMatchSampleSize),
  },
  {
    key: 'priceVariancePct',
    header: 'Variación de precio',
    render: (row) => formatRate(row.priceVariancePct, row.priceVarianceSampleSize),
  },
]

/** NXR-REQ-0058 (Supplier Performance): cada métrica se calcula en vivo
 * desde PO/GoodsReceipt/ThreeWayMatchResult reales
 * (`reporting_service.supplier_performance`) -- nunca fabricada. "Sin
 * datos suficientes" se muestra explícitamente en vez de un 0%/100%
 * engañoso cuando el proveedor todavía no tiene volumen real (`n`
 * expone el tamaño de muestra exacto detrás de cada tasa). */
export function SupplierPerformancePage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()

  const reportQuery = useQuery({
    queryKey: ['reports', 'supplier-performance', activeCompanyId],
    queryFn: () => reportingService.getSupplierPerformance(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="🤝"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

  const rows = reportQuery.data ?? []

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Desempeño de Proveedores</h1>
      </header>

      {reportQuery.isLoading ? (
        <LoadingState label="Cargando desempeño de proveedores…" />
      ) : reportQuery.isError ? (
        <ErrorState onRetry={() => reportQuery.refetch()} />
      ) : (
        <Card>
          <Table
            columns={COLUMNS}
            rows={rows}
            getRowKey={(row) => row.supplierId}
            emptyMessage="Sin proveedores registrados todavía."
          />
        </Card>
      )}
    </div>
  )
}
