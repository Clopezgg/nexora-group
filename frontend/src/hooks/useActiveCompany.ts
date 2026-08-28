import { useMemo, useSyncExternalStore } from 'react'
import { useQuery } from '@tanstack/react-query'
import { masterDataService } from '../services/masterDataService'

const STORAGE_KEY = 'nexora.activeCompanyId'
let selectedCompanyId: string | null =
  typeof window !== 'undefined' ? window.localStorage.getItem(STORAGE_KEY) : null
const listeners = new Set<() => void>()

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function getSnapshot() {
  return selectedCompanyId
}

function setSelectedCompanyId(value: string | null) {
  selectedCompanyId = value
  if (typeof window !== 'undefined') {
    if (value) window.localStorage.setItem(STORAGE_KEY, value)
    else window.localStorage.removeItem(STORAGE_KEY)
  }
  listeners.forEach((listener) => listener())
}

/**
 * Selección global de compañía. Todos los consumidores comparten el mismo
 * TanStack Query cache y el mismo ID seleccionado, evitando que cada página
 * mantenga una compañía distinta de forma accidental.
 */
export function useActiveCompany() {
  const companiesQuery = useQuery({
    queryKey: ['master-data', 'companies'],
    queryFn: masterDataService.listCompanies,
  })
  const selectedId = useSyncExternalStore(subscribe, getSnapshot, getSnapshot)
  const companies = useMemo(
    () => (Array.isArray(companiesQuery.data) ? companiesQuery.data : []),
    [companiesQuery.data],
  )
  const selectedExists = selectedId ? companies.some((company) => company.id === selectedId) : false
  const activeCompanyId = selectedExists ? selectedId : companies[0]?.id ?? null
  const activeCompany = companies.find((company) => company.id === activeCompanyId) ?? null

  return {
    companies,
    activeCompany,
    activeCompanyId,
    setActiveCompanyId: setSelectedCompanyId,
    isLoading: companiesQuery.isLoading,
    isError: companiesQuery.isError,
    refetch: companiesQuery.refetch,
  }
}
