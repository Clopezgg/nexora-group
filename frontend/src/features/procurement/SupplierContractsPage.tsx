import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Badge, Button, Card, EmptyState, ErrorState, Input, LoadingState, Modal, Select, Table } from '../../design-system'
import type { TableColumn } from '../../design-system'
import { useActiveCompany } from '../../hooks/useActiveCompany'
import { procurementService } from '../../services/procurementService'
import { projectService } from '../../services/projectService'
import type { SupplierContract } from '../../types/procurement'

const emptyForm = {
  supplierId: '',
  projectId: '',
  contractNumber: '',
  value: '',
  currencyCode: 'HNL',
  startDate: '',
  advancePercentage: '',
  retentionPercentage: '',
}

/** NXR-REQ-0059/0060. `/abastecimiento/contratos` ya existía como entrada
 * reservada ("Contratos") en navigation.ts -- no se inventó ruta nueva.
 * `SupplierContract` cubre tanto Supplier Contracts como Subcontracts
 * (mismo modelo, sin campo distintivo -- ver la fila de trazabilidad).
 * `projectId` es opcional: un contrato general de la compañía no requiere
 * proyecto. */
export function SupplierContractsPage() {
  const { activeCompanyId, isLoading: loadingCompanies } = useActiveCompany()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [form, setForm] = useState(emptyForm)

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
  const projectsQuery = useQuery({
    queryKey: ['projects', activeCompanyId],
    queryFn: () => projectService.list(activeCompanyId as string),
    enabled: Boolean(activeCompanyId),
  })

  const suppliers = suppliersQuery.data ?? []
  const projects = projectsQuery.data ?? []
  const supplierNameById = new Map(suppliers.map((s) => [s.id, s.legalName]))

  const createMutation = useMutation({
    mutationFn: () =>
      procurementService.createContract({
        companyId: activeCompanyId as string,
        supplierId: form.supplierId,
        projectId: form.projectId || undefined,
        contractNumber: form.contractNumber,
        value: form.value,
        currencyCode: form.currencyCode,
        startDate: form.startDate,
        advancePercentage: form.advancePercentage || undefined,
        retentionPercentage: form.retentionPercentage || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['procurement', 'contracts', activeCompanyId] })
      setModalOpen(false)
      setForm(emptyForm)
    },
  })

  const columns: TableColumn<SupplierContract>[] = [
    { key: 'contractNumber', header: 'Número', render: (row) => row.contractNumber },
    {
      key: 'supplierId',
      header: 'Proveedor',
      render: (row) => supplierNameById.get(row.supplierId) ?? row.supplierId,
    },
    { key: 'value', header: 'Valor', render: (row) => row.value },
    { key: 'advancePercentage', header: 'Anticipo %', render: (row) => row.advancePercentage },
    { key: 'retentionPercentage', header: 'Retención %', render: (row) => row.retentionPercentage },
    { key: 'status', header: 'Estado', render: (row) => <Badge>{row.status}</Badge> },
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

      <Card>
        {contractsQuery.isLoading ? (
          <LoadingState label="Cargando contratos…" />
        ) : contractsQuery.isError ? (
          <ErrorState onRetry={() => contractsQuery.refetch()} />
        ) : (
          <Table
            columns={columns}
            rows={contractsQuery.data ?? []}
            getRowKey={(row) => row.id}
            emptyMessage="Aún no hay contratos registrados."
          />
        )}
      </Card>

      <Modal open={modalOpen} title="Nuevo contrato" onClose={() => setModalOpen(false)}>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            createMutation.mutate()
          }}
        >
          <Select
            name="supplierId"
            label="Proveedor"
            value={form.supplierId}
            onChange={(e) => setForm({ ...form, supplierId: e.target.value })}
            required
          >
            <option value="" disabled>
              Selecciona un proveedor
            </option>
            {suppliers.map((s) => (
              <option key={s.id} value={s.id}>
                {s.legalName}
              </option>
            ))}
          </Select>
          <Select
            name="projectId"
            label="Proyecto (opcional)"
            value={form.projectId}
            onChange={(e) => setForm({ ...form, projectId: e.target.value })}
          >
            <option value="">General (sin proyecto)</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </Select>
          <Input
            name="contractNumber"
            label="Número de contrato"
            value={form.contractNumber}
            onChange={(e) => setForm({ ...form, contractNumber: e.target.value })}
            required
          />
          <Input
            name="value"
            label="Valor"
            value={form.value}
            onChange={(e) => setForm({ ...form, value: e.target.value })}
            required
          />
          <Input
            name="startDate"
            label="Fecha de inicio"
            type="date"
            value={form.startDate}
            onChange={(e) => setForm({ ...form, startDate: e.target.value })}
            required
          />
          <Input
            name="advancePercentage"
            label="Anticipo %"
            value={form.advancePercentage}
            onChange={(e) => setForm({ ...form, advancePercentage: e.target.value })}
          />
          <Input
            name="retentionPercentage"
            label="Retención %"
            value={form.retentionPercentage}
            onChange={(e) => setForm({ ...form, retentionPercentage: e.target.value })}
          />
          <Button
            type="submit"
            loading={createMutation.isPending}
            disabled={!form.supplierId || !form.contractNumber || !form.value || !form.startDate}
          >
            Guardar
          </Button>
          {createMutation.isError ? (
            <p className="nx-field__error">{String(createMutation.error)}</p>
          ) : null}
        </form>
      </Modal>
    </div>
  )
}
