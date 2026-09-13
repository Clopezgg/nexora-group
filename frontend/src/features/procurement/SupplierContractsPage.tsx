import { useState } from 'react'
import { useQueries, useQuery } from '@tanstack/react-query'
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  FilterBar,
  Input,
  LoadingState,
  Modal,
  Select,
  Table,
} from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { contractPaymentService } from '../../services/contractPaymentService'
import { ApiError } from '../../services/httpClient'
import { procurementService } from '../../services/procurementService'
import {
  SUPPLIER_CONTRACT_CATEGORY_LABELS,
  type SupplierContract,
  type SupplierContractCategory,
} from '../../types/procurement'
import { formatMoney } from '../../utils/currency'
import { supplierContractStatusLabel, supplierPartyRoleLabel } from '../../utils/statusLabels'
import { ContractPaymentPlanModal } from './ContractPaymentPlanModal'
import { ExecutionContractForm } from './ExecutionContractForm'

export function SupplierContractsPage() {
  const { activeCompanyId, activeCompany, isLoading: loadingCompanies } = useActiveCompany()
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
  const contracts = contractsQuery.data ?? []
  const suppliers = suppliersQuery.data ?? []
  const supplierById = new Map(suppliers.map((supplier) => [supplier.id, supplier]))

  const scheduleQueries = useQueries({
    queries: contracts.map((contract) => ({
      queryKey: ['contract-payments', 'by-contract', contract.id],
      queryFn: () => contractPaymentService.getByContract(contract.id),
      retry: false,
    })),
  })
  const summaryQueries = useQueries({
    queries: contracts.map((contract, index) => ({
      queryKey: ['contract-payments', 'summary', scheduleQueries[index]?.data?.id, contract.id],
      queryFn: () => contractPaymentService.summary(scheduleQueries[index]!.data!.id),
      enabled: Boolean(scheduleQueries[index]?.data?.id),
    })),
  })
  const contractIndex = new Map(contracts.map((contract, index) => [contract.id, index]))

  const columns: TableColumn<SupplierContract>[] = [
    { key: 'contractNumber', header: 'Contrato', render: (row) => row.contractNumber },
    {
      key: 'supplierId',
      header: 'Tercero',
      render: (row) => {
        const party = supplierById.get(row.supplierId)
        return party
          ? `${supplierPartyRoleLabel(party.partyRole)} · ${party.tradeName || party.legalName}`
          : 'Tercero no disponible'
      },
    },
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
      key: 'value',
      header: 'Valor contractual',
      numeric: true,
      render: (row) => formatMoney(row.value, row.currencyCode),
    },
    {
      key: 'advance',
      header: 'Anticipo pactado',
      numeric: true,
      render: (row) => formatMoney(row.advanceAmount ?? '0', row.currencyCode),
    },
    {
      key: 'paid',
      header: 'Pagado acumulado',
      numeric: true,
      render: (row) => {
        const index = contractIndex.get(row.id)
        const summary = index == null ? undefined : summaryQueries[index]?.data
        return summary ? formatMoney(summary.paidAccumulated, row.currencyCode) : '—'
      },
    },
    {
      key: 'balance',
      header: 'Saldo',
      numeric: true,
      render: (row) => {
        const index = contractIndex.get(row.id)
        const summary = index == null ? undefined : summaryQueries[index]?.data
        return summary ? formatMoney(summary.contractBalance, row.currencyCode) : '—'
      },
    },
    {
      key: 'next',
      header: 'Próximo vencimiento',
      render: (row) => {
        const index = contractIndex.get(row.id)
        const summary = index == null ? undefined : summaryQueries[index]?.data
        const scheduleError = index == null ? null : scheduleQueries[index]?.error
        const noSchedule = scheduleError instanceof ApiError && scheduleError.status === 404
        if (noSchedule)
          return row.paymentTermsType === 'LUMP_SUM'
            ? 'Pago único (sin plan)'
            : 'Sin plan de pagos'
        return summary?.nextDuePeriod
          ? `${summary.nextDuePeriod} · ${formatMoney(summary.nextDueAmount ?? '0', row.currencyCode)}`
          : '—'
      },
    },
    {
      key: 'status',
      header: 'Estado',
      render: (row) => <Badge>{supplierContractStatusLabel(row.status)}</Badge>,
    },
    {
      key: 'plan',
      header: 'Acciones',
      render: (row) => (
        <Button variant="secondary" onClick={() => setPlanContract(row)}>
          Plan y obligaciones
        </Button>
      ),
    },
  ]

  if (loadingCompanies) return <LoadingState label="Cargando compañías…" />
  if (!activeCompanyId || !activeCompany) {
    return (
      <EmptyState
        title="Selecciona una compañía"
        description="Los contratos de ejecución requieren una compañía activa explícita."
      />
    )
  }
  if (!activeCompany.functionalCurrencyCode) {
    return (
      <EmptyState
        icon="warning"
        title="La compañía activa no tiene moneda funcional"
        description="Configura la moneda funcional antes de crear contratos de ejecución."
      />
    )
  }

  return (
    <div>
      <header className="nx-page__header">
        <div>
          <h1 className="nx-dashboard__title">Contratos de ejecución</h1>
          <p className="nx-field__hint">
            Valor → anticipo → pagado → saldo → próxima obligación. Los porcentajes técnicos viven
            en el detalle, no dominan la operación diaria.
          </p>
        </div>
        <Button onClick={() => setModalOpen(true)} disabled={suppliers.length === 0}>
          Nuevo contrato
        </Button>
      </header>
      {suppliers.length === 0 ? (
        <p className="nx-field__error">
          Necesitas al menos un proveedor o contratista registrado primero.
        </p>
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
          onChange={(event) => setFilterNumber(event.target.value)}
          placeholder="Buscar…"
        />
        <Select
          label="Categoría"
          value={filterCategory}
          onChange={(event) => setFilterCategory(event.target.value)}
        >
          <option value="">Todas</option>
          {(Object.keys(SUPPLIER_CONTRACT_CATEGORY_LABELS) as SupplierContractCategory[]).map(
            (category) => (
              <option key={category} value={category}>
                {SUPPLIER_CONTRACT_CATEGORY_LABELS[category]}
              </option>
            ),
          )}
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
            rows={contracts.filter(
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

      <Modal
        open={modalOpen}
        title="Nuevo contrato de ejecución"
        onClose={() => setModalOpen(false)}
      >
        <ExecutionContractForm
          defaultCurrency={activeCompany.functionalCurrencyCode}
          onCancel={() => setModalOpen(false)}
          onCreated={() => setModalOpen(false)}
        />
      </Modal>
      {planContract ? (
        <ContractPaymentPlanModal
          contract={planContract}
          currencyCode={planContract.currencyCode}
          onClose={() => setPlanContract(null)}
        />
      ) : null}
    </div>
  )
}
