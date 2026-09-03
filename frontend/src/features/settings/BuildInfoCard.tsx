import { useQuery } from '@tanstack/react-query'
import { Card, LoadingState } from '../../design-system'
import { versionService } from '../../services/versionService'

/** ORDEN MAESTRA §21: permite certificar visualmente que origin/main == CI
 * == imagen backend == build frontend == producción, sin exponer secretos. */
export function BuildInfoCard() {
  const versionQuery = useQuery({
    queryKey: ['version'],
    queryFn: versionService.get,
  })
  const frontendSha = import.meta.env.VITE_GIT_SHA || null

  if (versionQuery.isLoading) return <Card title="Versión"><LoadingState label="Cargando…" /></Card>
  // Respuesta inesperada (endpoint viejo, red intermedia, etc.): no renderizar
  // datos de build inventados ni reventar la página de Configuración.
  if (!versionQuery.data?.gitSha) return null

  const { gitSha, buildTime, environment } = versionQuery.data

  return (
    <Card title="Versión">
      <p className="nx-field__hint">
        Backend <strong>{gitSha === 'unknown' ? gitSha : gitSha.slice(0, 7)}</strong>
        {frontendSha ? (
          <>
            {' '}· Frontend <strong>{frontendSha === 'unknown' ? frontendSha : frontendSha.slice(0, 7)}</strong>
          </>
        ) : null}
        {' '}· Build {buildTime} · Entorno <strong>{environment}</strong>
      </p>
    </Card>
  )
}
