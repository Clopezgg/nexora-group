import { apiFetch } from './httpClient'
import type { SearchResult } from '../types/search'

/** Global Search (NXR-REQ-0092). GET /api/search -- no /api/v1 prefix. */
export async function globalSearch(companyId: string, query: string): Promise<SearchResult[]> {
  if (query.trim().length < 2) return []
  const params = new URLSearchParams({ companyId, q: query })
  return apiFetch<SearchResult[]>(`/search?${params.toString()}`)
}
