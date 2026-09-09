# Theme Engine

Nexora ofrece cinco familias visuales, en este orden estable: **NEXORA**, **Horizon**, **Quartz**, **Belize** y **SAP GUI**. Un tema sólo controla presentación; no modifica datos, cifras, permisos, rutas, Company Scope, Project Scope, Protected Edit, contabilización, workflows ni contratos API.

## SAP GUI

La quinta familia se reconstruyó en React y CSS usando como referencia visual el archivo `sap-widgets.jpl` proporcionado por el usuario. Se inspeccionaron sus familias `SAP-Signature` y `SAP-Tradeshow`, widgets de Screen, Tree, Tabs, Titled Box, Field, Button, Dialog y toolbar, sus relaciones de color, dimensiones y eventos declarativos. Nexora no ejecuta ni distribuye el paquete, no rasteriza pantallas completas y no depende de SAP GUI, SAP backend, SAPUI5, RFC/BAPI o ABAP. Sin afiliación con SAP. Mapeo explícito widget por widget en `docs/SAP_GUI_JPL_MAPPING.md`.

Los IDs persistentes son:

- `sap-gui-signature`: acero azul claro, árbol Easy Access, toolbar Signature, fields azules al foco, tabs tipo carpeta y titled boxes.
- `sap-gui-tradeshow`: chrome azul profundo, title strips, toolbar y grids con bandas, tabs elevadas y paneles de mayor contraste.
- `sap-gui-horizon`: workstation SAP modernizada con lenguaje Horizon (70% SAP GUI + 30% modernización: superficies limpias, bordes finos, foco contemporáneo, iconografía lineal). Sigue siendo workstation densa con tree, command field, toolbar, screen, grid y status bar — nunca Fiori/launchpad.
- `sap-gui-horizon-dark`: la misma workstation en modo oscuro real con jerarquía tonal (nunca simple inversión de colores).

Los cuatro presets recomiendan densidad `compact`, conservan `comfortable` y `finance-dense`, y exponen `data-nx-family="sap-gui"`, `data-nx-anatomy`, `data-nx-sap-variant` más datasets estructurales (`data-nx-shell`, `data-nx-navigation`, `data-nx-menubar`, `data-nx-commandbar`, `data-nx-toolbar`, `data-nx-screen`, `data-nx-tabs`, `data-nx-panel`, `data-nx-field`, `data-nx-button`, `data-nx-table`, `data-nx-dialog`, `data-nx-statusbar`) en el elemento raíz. `ThemeAnatomy` es autoridad ejecutable: shell, navegación, menubar, command bar, toolbar, screen, headers, tree, tabs, panels, fields, selects, buttons, tables, dialogs, status bar, densidad e iconografía; el CSS razona por anatomía, no solo por familia/variante (`compileTheme()` emite `--nx-anatomy-*`).

**Horizon (familia) ≠ SAP GUI Horizon (variante).** La familia `Horizon` es la familia moderna actual de Nexora; la variante `sap-gui-horizon` vive bajo `family='sap-gui'` y es una workstation SAP modernizada.

## Workstation (`frontend/src/layouts/sap/`)

`SapWorkstation` es composición de presentación: `SapTitleBar`, `SapMenuBar` (Sistema/Editar/Navegar/Extras/Ayuda, todo real; sin Favoritos porque no hay persistencia; sin códigos SAP falsos), `SapCommandBar` (módulos RBAC en local + `globalSearch` remoto), `SapToolbar` (navegación real de sesión), `SapEasyAccessTree` (expansión por grupo, teclado completo, typeahead, ARIA viva), `SapScreenFrame` (`Outlet` real con título/contexto), `SapStatusBar` (estado, compañía, proyecto/vista, período fiscal + estado, Protected Edit, usuario) y `Topbar`/`Drawer`/`CommandPalette` canónicos. No duplica Router, auth, permisos ni datos.

## Confirmación y persistencia

Seleccionar manualmente SAP GUI desde otra familia abre **Cambiar a SAP GUI** antes de alterar el draft o el preview. Cancelar conserva la interfaz previa; aceptar inicia un preview global de Signature sin persistir. Cambiar entre las cuatro variantes SAP o salir hacia otra familia no vuelve a preguntar. Cargar una preferencia SAP ya guardada tampoco muestra el diálogo.

La cascada existente permanece: preview → preferencia de usuario → predeterminado de compañía → NEXORA default. Sólo **Guardar como mi preferencia** persiste el draft; la compañía puede guardar cualquiera de los cuatro IDs mediante la configuración existente. El backend ya almacena IDs visuales como strings limitados, por lo que no requiere migración.

## Adaptación

En desktop, SAP GUI usa title bar, menubar, command field, toolbar, árbol permission-aware, work screen y status bar. En tablet el árbol pasa al drawer existente; en móvil, menubar/toolbar permiten overflow, command field adaptado, status bar reducida, los campos recuperan targets táctiles (≥40px) y las tablas conservan su estrategia responsive. El árbol reutiliza las rutas y reglas de visibilidad canónicas.

La reconstrucción mantiene foco visible, navegación de teclado (árbol, menús, tabs, diálogos), nombres accesibles, semántica de estados, contraste legible (AA en las cuatro variantes; AAA en alto contraste), Escape y focus trap en diálogos, restauración de foco y `prefers-reduced-motion`. La mini-aplicación de vista previa representa las cuatro variantes de forma distinguible sin cifras financieras ficticias. La fidelidad a controles compactos nunca reduce los targets móviles ni el tamaño del texto crítico a valores ilegibles.
