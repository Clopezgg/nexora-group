import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { masterDataService } from '../services/masterDataService'

/**
 * Selección de compañía activa para pantallas que necesitan companyId
 * (multi-company real desde el modelo, orden maestra §15). Por ahora vive a
 * nivel de cada página -- cuando exista un selector global de compañía en el
 * Topbar (Track G/Platform) esto se puede centralizar sin cambiar el
 * contrato de las páginas que ya lo usan.
 */
export function useActiveCompany() {
  const companiesQuery = useQuery({
    queryKey: ['master-data', 'companies'],
    queryFn: masterDataService.listCompanies,
  })
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const companies = useMemo(() => companiesQuery.data ?? [], [companiesQuery.data])
  const activeCompanyId = useMemo(
    () => selectedId ?? companies[0]?.id ?? null,
    [selectedId, companies],
  )

  return {
    companies,
    activeCompanyId,
    setActiveCompanyId: setSelectedId,
    isLoading: companiesQuery.isLoading,
    isError: companiesQuery.isError,
    refetch: companiesQuery.refetch,
  }
}
