import { Tabs } from '../../design-system'
import { SubmittalsPage } from '../submittals/SubmittalsPage'
import { RfiPage } from './RfiPage'

// El menú de navegación (navigation.ts, compartido con Task 3 -- no se
// modifica aquí) tiene un único ítem `/proyectos/rfi-submittals` para ambos
// dominios (RFI y Submittals son entidades independientes, con sus propios
// modelo/servicio/ruta -- ver docs/REQUIREMENTS_TRACEABILITY.md
// NXR-REQ-0085/0086). Esta página compuesta los presenta como dos tabs
// reales sobre esa única ruta, sin inventar un segundo ítem de navegación.
export function RfiSubmittalsPage() {
  return (
    <Tabs
      items={[
        { key: 'rfi', label: 'RFI', content: <RfiPage /> },
        { key: 'submittals', label: 'Submittals', content: <SubmittalsPage /> },
      ]}
    />
  )
}
