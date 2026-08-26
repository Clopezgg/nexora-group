import { useQuery } from '@tanstack/react-query'
import { masterDataService } from '../services/masterDataService'

/**
 * DEFERRED-FINAL-015: directorio real de usuarios de una compañía, para
 * reemplazar los campos de texto libre UUID que QualityPage/SafetyPage/
 * AccountsPayablePage usaban antes por falta de este endpoint.
 */
export function useCompanyUsers(companyId: string | null | undefined) {
  const query = useQuery({
    queryKey: ['master-data', 'users', companyId],
    queryFn: () => masterDataService.listUsers(companyId as string),
    enabled: Boolean(companyId),
  })
  return { users: query.data ?? [], isLoading: query.isLoading, isError: query.isError }
}
