import { Combobox, type ComboboxOption } from './FormControls'
import { EmptyState } from './States'

export interface EntitySelectorOption {
  id: string
  label: string
  description?: string
}

interface EntitySelectorProps {
  label: string
  placeholder?: string
  options: EntitySelectorOption[]
  value: string | null
  onChange: (id: string | null) => void
  disabled?: boolean
  emptyLabel: string
}

/**
 * Generic, backend-agnostic picker for a master-data entity (company, project,
 * WBS, supplier, customer, account, warehouse, …). Each domain track wires it
 * to its own list endpoint once that endpoint exists; until then a call site
 * passes `options={[]}` and this renders an honest empty state instead of
 * fabricating rows.
 */
export function EntitySelector({
  label,
  placeholder,
  options,
  value,
  onChange,
  disabled,
  emptyLabel,
}: EntitySelectorProps) {
  if (options.length === 0) {
    return <EmptyState icon="folder" title={emptyLabel} />
  }
  const comboOptions: ComboboxOption[] = options.map((option) => ({
    value: option.id,
    label: option.label,
  }))
  return (
    <Combobox
      label={label}
      placeholder={placeholder}
      options={comboOptions}
      value={value}
      onChange={onChange}
      disabled={disabled}
    />
  )
}

type DomainSelectorProps = Omit<EntitySelectorProps, 'label' | 'emptyLabel'>

export function CompanySelector(props: DomainSelectorProps) {
  return <EntitySelector {...props} label="Empresa" emptyLabel="Aún no hay empresas configuradas." />
}

export function ProjectSelector(props: DomainSelectorProps) {
  return (
    <EntitySelector {...props} label="Proyecto" emptyLabel="Aún no hay proyectos disponibles." />
  )
}

export function WBSSelector(props: DomainSelectorProps) {
  return <EntitySelector {...props} label="WBS" emptyLabel="Este proyecto aún no tiene WBS." />
}

export function SupplierSelector(props: DomainSelectorProps) {
  return (
    <EntitySelector {...props} label="Proveedor" emptyLabel="Aún no hay proveedores registrados." />
  )
}

export function CustomerSelector(props: DomainSelectorProps) {
  return (
    <EntitySelector {...props} label="Cliente" emptyLabel="Aún no hay clientes registrados." />
  )
}

export function AccountSelector(props: DomainSelectorProps) {
  return (
    <EntitySelector
      {...props}
      label="Cuenta contable"
      emptyLabel="El catálogo de cuentas aún no está disponible."
    />
  )
}

export function WarehouseSelector(props: DomainSelectorProps) {
  return (
    <EntitySelector {...props} label="Almacén" emptyLabel="Aún no hay almacenes configurados." />
  )
}
