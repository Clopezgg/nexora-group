import { useActiveCompany } from '../../hooks/useActiveCompany'

/** Barra de título de la workstation: nombre del sistema + compañía activa. */
export function SapTitleBar() {
  const { activeCompany } = useActiveCompany()
  return (
    <div className="nx-sap-titlebar" role="banner" aria-label="Barra de título SAP GUI">
      <strong>NEXORA — Gestión empresarial</strong>
      <span>{activeCompany?.name ?? 'Empresa no seleccionada'}</span>
    </div>
  )
}
