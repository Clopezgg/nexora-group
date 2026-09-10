# SAP GUI — Mapeo explícito del JPL (`sap-widgets.jpl`)

Fuente visual autoritativa: `~/Downloads/sap-widgets.jpl` (Justinmind 8.5.0,
agosto 2018). Contiene 2 grupos (`SAP-Signature`, `SAP-Tradeshow`), 26
widgets y ~138 assets en `images/`. El JPL **no se ejecuta**: es referencia
visual. Nexora lo recrea con React/CSS/SVG sin runtime, backend, logos ni
librerías de SAP. Sin afiliación con SAP.

Inspección obligatoria cubierta: `info.xml`, `widgets.xml`, familias
Signature/Tradeshow, Main Screen, Screen, Tree, Left bar, Tabs/Tab/Sel Tab,
Item/Sel Item, Field/Blue field, Button, Toolbar/Home toolbar/Tool item,
Titled Box/Box, Select, Dialog, estados selected, paleta, bordes,
tipografía, spacing y jerarquías.

## Paleta derivada del JPL (no "parece SAP")

Clásicos verificados en `widgets.xml` y reutilizados como constantes de
fidelidad bajo `[data-nx-family='sap-gui']`: `#668DB5 #182A53 #6289AE
#466DBD #87ABD6 #172E50 #21386B #265B8F #233866 #C8C8C8 #A8B8C7 #C3CCD7
#DFEBF5 #CBD4E1 #D6DBE5 #EAF1F6 #000000 #FFFFFF`. Horizon/Horizon Dark usan
paletas nuevas propias (azul `#0A6ED1`, dark tonal `#0D141D…#1E2B3A`) sin
copiar productos SAP externos.

## Tabla de mapeo JPL → Nexora

| JPL COMPONENT | NEXORA IMPLEMENTATION | TOKEN / ANATOMY | STATUS |
|---|---|---|---|
| Main Screen | `SapWorkstation` (`layouts/sap/`) + grid shell en `AppLayout.css` | `anatomy.shellMode='workstation'`, `data-nx-shell` | COMPLETE |
| Screen | `SapScreenFrame` (título + contexto + work area, `Outlet` real) | `contentFrameMode='screen'/'work-screen'`, `data-nx-screen` | COMPLETE |
| Left bar | `aside.nx-sidebar` + `SapEasyAccessTree` (permisionado por RBAC) | `navigationMode='tree'`, `data-nx-navigation` | COMPLETE |
| Tree | `SapEasyAccessTree`: `expandedGroups` real, roving tabindex, typeahead, `role=tree/treeitem/group`, `aria-expanded/selected/level/current` | `treeMode='easy-access'`, `--nx-anatomy-tree-mode` | COMPLETE |
| Item | `NavLink` con `nx-sidebar__link`, icono del design system | `--nx-shell-sidebar-*` | COMPLETE |
| Sel Item | `nx-sidebar__link--active` + `aria-selected/aria-current='page'` | `sidebarActiveBg/Text` | COMPLETE |
| Tabs | `.nx-tabs__*` folder (Signature), raised-folder (Tradeshow), modern-folder híbrido (Horizon) | `tabsMode`, `data-nx-tabs` | COMPLETE |
| Tab | `.nx-tabs__tab` clásica | — | COMPLETE |
| Sel Tab | `.nx-tabs__tab--active` + panel `.nx-tabs__panel` | — | COMPLETE |
| Field | `.nx-input/.nx-select/.nx-textarea` compactos 28–30px, inset shadow clásica | `fieldMode='classic-blue'/'tradeshow-blue'/'horizon-compact'/'horizon-dark-compact'`, `data-nx-field` | COMPLETE |
| Blue field | `:focus` `#DFEAF3/#C2D8EB` + borde `#466DBD` (clásicas); anillo moderno en Horizon | `--nx-focus-ring` | COMPLETE |
| Select | `selectMode='classic'/'modern-compact'/'dark-compact'`, `--nx-anatomy-select-mode` | `data-nx-field` + overrides | COMPLETE |
| Button | `.nx-button` bevel/gradient (clásicas), plana con borde fino (Horizon) | `buttonMode='beveled'/'gradient'/'horizon-tool'/'horizon-dark-tool'`, `data-nx-button` | COMPLETE |
| Toolbar | `SapToolbar` (atrás/adelante/inicio/búsqueda/navegación reales) + `Topbar` con tratamiento SAP | `toolbarMode='signature'/'tradeshow'/'horizon'/'horizon-dark'`, `data-nx-toolbar` | COMPLETE |
| Home toolbar | `SapCommandBar`: `[✓][←][→][campo][▾]` con resultados locales RBAC + `globalSearch` remoto | `commandBarMode='sap-command'`, `data-nx-commandbar` | COMPLETE |
| Tool item | Botones del commandbar/toolbar, iconografía del design system (sin emojis) | `iconTreatment='classic-16'/'line'` | COMPLETE |
| Box | `.nx-card/.nx-chart-card/.nx-stat-card` borde clásico sin bevel moderno | `panelMode`, `data-nx-panel` | COMPLETE |
| Titled Box | Card con título 12px + `banded-box`/`modern-titled-box`/`dark-titled-box` por variante | `panelMode`, `--nx-anatomy-panel-mode` | COMPLETE |
| Dialog | `Modal` existente (focus trap, Escape, restore focus, `aria-labelledby/describedby`) + ventana clásica/moderna/dark | `dialogMode='window'/'window-banded'/'horizon-window'/'horizon-window-dark'`, `data-nx-dialog` | COMPLETE |
| Label | `.nx-field__label` 11px Arial (clásicas) / 11.5px semibold (Horizon) | `--nx-field-label-*` | COMPLETE |
| Text | Tipografía base 13px Arial (clásicas) / Inter (Horizon) | `--nx-font-*` | COMPLETE |
| Menu bar | `SapMenuBar`: Sistema/Editar/Navegar/Extras/Ayuda, todo real (sin Favoritos: no hay persistencia; sin códigos SAP falsos) | `menuBarMode='classic'/'classic-modern'`, `data-nx-menubar` | COMPLETE |
| Status bar | `SapStatusBar`: Listo/compañía/proyecto-período+estado/Protected Edit/usuario, todo real | `statusBarMode='context'`, `data-nx-statusbar` | COMPLETE |

Assets del JPL (`images/*.bmp/.gif/.png`): **no se copia ninguno**. Toda la
fidelidad se recrea con CSS/SVG/iconos del design system; los BMP/GIF de
2018 no aportan fidelidad imposible de recrear y degradarían startup.

## Auditoría de estilos que escapan del Theme Engine (§29)

Método: búsqueda de `#[hex]`, `box-shadow`, `border-radius` y componentes
locales (tablas, modales, tabs, cards, drawers, filter bars) en
`frontend/src`, clasificados por capa:

- **Capa base** (`design-system/nexora-theme.css`, `primitives.css`):
  hardcoded como *fallbacks* pre-tema; siempre pisados por las reglas
  `data-nx-themed='on'` de `themes.css`. Arquitectura intencional, no fuga.
- **Capa SAP** (`themes.css` + `AppLayout.css` bajo
  `[data-nx-family='sap-gui']` / `[data-nx-sap-variant]`): constantes JPL
  intencionales + `var(--x, fallback)`. Sin fuga a familias modernas
  (verificado por test `no monta chrome SAP GUI` y E2E `modern family`).
- **Superficies globales** (cards, tablas, formularios, botones, diálogos,
  drawers, filter-bars, object-headers, badges, tabs, charts, stat cards,
  page/object headers, sidebar, topbar, bottom-nav): todas tienen override
  SAP; las rutas heredan SAP GUI sin reescritura por página.
- **Densidad**: `compact` por defecto en las 4 variantes SAP;
  `comfortable` y `finance-dense` conservadas y funcionales.

Resultado: `NO_HARDCODED_THEME_LEAKS=PASS` (con la salvedad documentada de
fallbacks base, que son parte del diseño por capas).
