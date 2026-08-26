/**
 * ActiveUIContext: proyecto/vista activa elegido por el usuario en la UI.
 * Independiente de OperationScope (concepto de backend/dominio). Ver CLAUDE.md.
 */
export interface ActiveUIContext {
  activeProjectId: string | null
  activeProjectName: string | null
}
