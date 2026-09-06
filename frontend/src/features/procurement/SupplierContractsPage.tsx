import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Badge, Button, Card, EmptyState, ErrorState, FilterBar, Input, LoadingState, Modal, Select, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { procurementService } from '../../services/procurementService'
import { formatMoney } from '../../utils/currency'
import { ContractPaymentPlanModal } from './ContractPaymentPlanModal'
import { ExecutionContractForm } from './ExecutionContractForm'
import {
  SUPPLIER_CONTRACT_CATEGORY_LABELS,
  type SupplierContract,
  type SupplierContractCategory,
} from '../../types/procurement'
import { supplierContractStatusLabel } from '../../utils/statusLabels'

/** NXR-REQ-0059/0060. `/abastecimiento/contratos` ya existía como entrada
 * reservada ("Contratos") en navigation.ts -- no se inventó ruta nueva.
 * `SupplierContract` cubre tanto Supplier Contracts como Subcontracts
 * (mismo modelo, sin campo distintivo -- ver la fila de trazabilidad).
 * `projectId` es opcional: un contrato general de la compañía no requiere
 * proyecto. */
export function SupplierContractsPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const [modalOpen, setModalOpen] = useState(false)
  const [planContract, setPlanContract] = useState<SupplierContract | null>(null)
  const [filterCategory, setFilterCategory] = useState('')
  const [filterNumber, setFilterNumber] = useState('')

  const contractsQuery = useQuery({
    queryKey: ['procurement', 'contracts', activeCompanyId],
    queryFn: () => procurementService.listContracts(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })
  const suppliersQuery = useQuery({
    queryKey: ['procurement', 'suppliers', activeCompanyId],
    queryFn: () => procurementService.listSuppliers(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const suppliers = suppliersQuery.data ?? []
  const supplierNameById = new Map(suppliers.map((s) => [s.id, s.legalName]))

  const columns: TableColumn<SupplierContract>[] = [
    { key: 'contractNumber', header: 'Número', render: (row) => row.contractNumber },
    {
      key: 'contractCategory',
      header: 'Categoría',
      render: (row) => (
        <Badge tone="neutral">
          {SUPPLIER_CONTRACT_CATEGORY_LABELS[row.contractCategory] ?? row.contractCategory}
        </Badge>
      ),
    },
    {
      key: 'supplierId',
      header: 'Proveedor',
      render: (row) => supplierNameById.get(row.supplierId) ?? row.supplierId,
    },
    { key: 'value', header: 'Valor', numeric: true, render: (row) => formatMoney(row.value, row.currencyCode) },
    { key: 'advancePercentage', header: 'Anticipo %', numeric: true, render: (row) => `${Number(row.advancePercentage).toFixed(2)}%` },
    { key: 'retentionPercentage', header: 'Retención %', numeric: true, render: (row) => `${Number(row.retentionPercentage).toFixed(2)}%` },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{supplierContractStatusLabel(row.status)}</Badge> },
    {
      key: 'plan',
      header: 'Plan de pagos',
      render: (row) => (
        <Button variant="secondary" onClick={() => setPlanContract(row)}>
          Ver plan
        </Button>
      ),
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId) {
    return (
      <EmptyState
        icon="file"
        title="Configura una compañía primero"
        description="No hay compañías registradas todavía."
      />
    )
  }

  return (
    <div>
      <header className="nx-page__header">
        <h1 className="nx-dashboard__title">Contratos y Subcontratos</h1>
        <Button onClick={() => setModalOpen(true)} disabled={suppliers.length === 0}>
          Nuevo contrato
        </Button>
      </header>
      {suppliers.length === 0 ? (
        <p className="nx-field__error">Necesitas al menos un proveedor registrado primero.</p>
      ) : null}

      <FilterBar
        onClear={() => {
          setFilterCategory('')
          setFilterNumber('')
        }}
      >
        <Input
          label="Filtrar por número"
          value={filterNumber}
          onChange={(e) => setFilterNumber(e.target.value)}
          placeholder="Buscar…"
        />
        <Select
          label="Filtrar por categoría"
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
        >
          <option value="">Todas</option>
          {(Object.keys(SUPPLIER_CONTRACT_CATEGORY_LABELS) as SupplierContractCategory[]).map((c) => (
            <option key={c} value={c}>
              {SUPPLIER_CONTRACT_CATEGORY_LABELS[c]}
            </option>
          ))}
        </Select>
      </FilterBar>

      <Card>
        {contractsQuery.isLoading ? (
          <LoadingState label="Cargando contratos…" />
        ) : contractsQuery.isError ? (
          <ErrorState onRetry={() => contractsQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={(contractsQuery.data ?? []).filter(
              (row) =>
                (!filterCategory || row.contractCategory === filterCategory) &&
                (!filterNumber ||
                  row.contractNumber.toLowerCase().includes(filterNumber.toLowerCase())),
            )}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay contratos registrados."
          />
        )}
      </Card>

      <Modal open={modalOpen} title="Nuevo contrato" onClose={() => setModalOpen(false)}>
        <ExecutionContractForm
          onCancel={() => setModalOpen(false)}
          onCreated={() => setModalOpen(false)}
        />
      </Modal>

      {planContract ? (
        <ContractPaymentPlanModal
          contract={planContract}
          currencyCode={planContract.currencyCode ?? 'HNL'}
          onClose={() => setPlanContract(null)}
        />
      ) : null}
    </div>
  )
}
