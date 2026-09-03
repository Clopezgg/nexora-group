import { apiFetch } from './httpClient'
import type { BuildInfo } from '../types/version'

export const versionService = {
  get: () => apiFetch<BuildInfo>('/version'),
}
