# Theme Engine

Nexora ofrece cinco familias visuales, en este orden estable: **NEXORA**, **Horizon**, **Quartz**, **Belize** y **SAP GUI**. Un tema sólo controla presentación; no modifica datos, cifras, permisos, rutas, Company Scope, Project Scope, Protected Edit, contabilización, workflows ni contratos API.

## SAP GUI

La quinta familia se reconstruyó en React y CSS usando como referencia visual el archivo `sap-widgets.jpl` proporcionado por el usuario. Se inspeccionaron sus familias `SAP-Signature` y `SAP-Tradeshow`, widgets de Screen, Tree, Tabs, Titled Box, Field, Button, Dialog y toolbar, sus relaciones de color, dimensiones y eventos declarativos. Nexora no ejecuta ni distribuye el paquete, no rasteriza pantallas completas y no depende de SAP GUI, SAP backend, SAPUI5, RFC/BAPI o ABAP.

Los IDs persistentes son:

- `sap-gui-signature`: acero azul claro, árbol Easy Access, toolbar Signature, fields azules al foco, tabs tipo carpeta y titled boxes.
- `sap-gui-tradeshow`: chrome azul profundo, title strips, toolbar y grids con bandas, tabs elevadas y paneles de mayor contraste.

Ambos presets recomiendan densidad `compact`, conservan `comfortable` y `finance-dense`, usan Arial/Helvetica/system-ui y exponen `data-nx-family="sap-gui"`, `data-nx-anatomy` y `data-nx-sap-variant` en el elemento raíz. `ThemeAnatomy` centraliza shell, navegación, menubar, command bar, toolbar, screen, headers, tree, tabs, panels, fields, buttons, tables, dialogs, status bar, densidad e iconografía.

## Confirmación y persistencia

Seleccionar manualmente SAP GUI desde otra familia abre **Cambiar a SAP GUI** antes de alterar el draft o el preview. Cancelar conserva la interfaz previa; aceptar inicia un preview global de Signature sin persistir. Cambiar Signature ↔ Tradeshow o salir hacia otra familia no vuelve a preguntar. Cargar una preferencia SAP ya guardada tampoco muestra el diálogo.

La cascada existente permanece: preview → preferencia de usuario → predeterminado de compañía → NEXORA default. Sólo **Guardar como mi preferencia** persiste el draft; la compañía puede guardar cualquiera de los dos IDs mediante la configuración existente. El backend ya almacena IDs visuales como strings limitados, por lo que no requiere migración.

## Adaptación

En desktop, SAP GUI usa window title, menubar, toolbar, árbol permission-aware, work screen y status bar. En tablet el árbol pasa al drawer existente; en móvil, menubar/toolbar permiten overflow, los campos recuperan targets táctiles y las tablas conservan su estrategia responsive. El árbol reutiliza las rutas y reglas de visibilidad canónicas.

La reconstrucción mantiene foco visible, navegación de teclado, nombres accesibles, semántica de estados, contraste legible, Escape y focus trap en diálogos, restauración de foco y `prefers-reduced-motion`. La fidelidad a controles compactos nunca reduce los targets móviles ni el tamaño del texto crítico a valores ilegibles.
