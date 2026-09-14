/**
 * NEXORA SAP GUI Classic — Screen Frame
 * 
 * Frame global para pantallas transaccionales:
 * - Título de pantalla
 * - Contexto (grupo de navegación)
 * - Área de trabajo
 * - Sin duplicar DOM destructivo
 */

import { Outlet, useLocation } from 'react-router-dom';
import { navGroups } from '../../app/navigation';
import '../../sap-gui/components/SapScreenFrame.css';

/**
 * Screen frame global: toda ruta principal en modo SAP se siente como una
 * Screen (título + contexto/breadcrumb + work area). No envuelve con DOM
 * destructivo: un encabezado visual + la ruta real debajo.
 */
export function SapScreenFrame() {
  const location = useLocation();

  // Búsqueda directa (~50 rutas): sin memo para no violar
  // react-hooks/preserve-manual-memoization sobre la constante de módulo.
  let screen = { group: 'NEXORA', title: 'Pantalla' };
  for (const group of navGroups) {
    for (const item of group.items) {
      if (location.pathname === item.path || location.pathname.startsWith(`${item.path}/`)) {
        screen = { group: group.label, title: item.label };
      }
    }
  }

  return (
    <div className="nx-sap-screen" data-testid="sap-screen-frame">
      <div className="nx-sap-screen__header">
        <span className="nx-sap-screen__title">{screen.title}</span>
        <span className="nx-sap-screen__context" aria-label="Contexto de pantalla">
          {screen.group}
        </span>
      </div>
      <div className="nx-sap-screen__workarea">
        <Outlet />
      </div>
    </div>
  );
}

export default SapScreenFrame;