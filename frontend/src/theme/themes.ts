/**
 * Enterprise Theme Architecture (ORDEN MAESTRA — FIORI / CASH FLOW / TREASURY
 * DIRECTION, §8-§11).
 *
 * REGLA (§68): un tema es PURAMENTE presentación. Nunca toca moneda,
 * cálculos, permisos, contabilidad, workflow ni estado de negocio.
 *
 * A diferencia del modelo anterior (un `vars: Record<string,string>` plano),
 * un `ThemePreset` ahora tiene DOMINIO TIPADO: `palette`, `typography`,
 * `shell`, `navigation`, `shape`, `elevation`, `motion`, `tables`, `forms`,
 * `buttons`, `dialogs`, `charts`, `iconography`, `focus`, `mobile`. El
 * compilador `compileTheme()` deriva las variables CSS de esa estructura —
 * cambiar de familia (Horizon / Quartz / Belize) cambia radio, elevación,
 * densidad base, tratamiento de tablas y tipografía, no solo el color.
 *
 * Sin CSS ni logos propietarios de SAP. Tipografías del sistema u
 * open-source (Inter).
 */

export type Density = 'comfortable' | 'compact' | 'finance-dense'
export type UiScale = 90 | 100 | 110
export type ThemeFamily = 'horizon' | 'quartz' | 'belize' | 'nexora'
export type ThemeContrast = 'normal' | 'high'

export interface ThemePalette {
  pageBg: string
  surface: string
  surfaceRaised: string
  surfaceSunken: string
  text: string
  textMuted: string
  textSubtle: string
  border: string
  borderStrong: string
  accent: string
  accentHover: string
  accentContrast: string
  positive: string
  negative: string
  warning: string
  info: string
}

export interface ThemeTypography {
  fontFamily: string
  fontFamilyMono: string
  /** px base — la escala tipográfica global. */
  baseSize: number
  headingWeight: number
  bodyWeight: number
  labelWeight: number
  headingTracking: string
}

export interface ThemeShell {
  style: 'solid-dark' | 'solid-light' | 'tinted'
  sidebarBg: string
  sidebarText: string
  sidebarActiveBg: string
  sidebarActiveText: string
  topbarBg: string
  topbarText: string
  topbarBorder: string
}

export interface ThemeShape {
  radiusXs: string
  radiusSm: string
  radiusMd: string
  radiusLg: string
  borderWidth: string
}

export interface ThemeElevation {
  card: string
  raised: string
  overlay: string
}

export interface ThemeMotion {
  durationFast: string
  durationBase: string
  easing: string
}

export interface ThemeTables {
  headerBg: string
  headerText: string
  rowHover: string
  stripe: string
  divider: string
}

export interface ThemeCharts {
  grid: string
  axis: string
  series: [string, string, string, string]
}

export interface ThemeIconography {
  style: 'line' | 'duotone'
  strokeWidth: string
}

export interface ThemeFocus {
  ring: string
  width: string
  offset: string
}

export interface ThemePreset {
  id: string
  name: string
  description: string
  family: ThemeFamily
  variant: string
  isDark: boolean
  contrast: ThemeContrast
  /** Densidad por defecto que sugiere la familia (el usuario la puede pisar). */
  densityDefault: Density
  palette: ThemePalette
  typography: ThemeTypography
  shell: ThemeShell
  shape: ThemeShape
  elevation: ThemeElevation
  motion: ThemeMotion
  tables: ThemeTables
  charts: ThemeCharts
  iconography: ThemeIconography
  focus: ThemeFocus
}

const INTER = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
const SYSTEM = "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
const MONO = "'JetBrains Mono', 'SFMono-Regular', ui-monospace, Menlo, Consolas, monospace"

// --------------------------------------------------------------------------
// Rasgos ESTRUCTURALES por familia — lo que distingue Horizon de Quartz de
// Belize más allá del color: radio, elevación, densidad, tipografía, tablas.
// --------------------------------------------------------------------------
interface FamilyTraits {
  shape: ThemeShape
  elevation: (dark: boolean) => ThemeElevation
  motion: ThemeMotion
  typographyBase: number
  headingTracking: string
  densityDefault: Density
  iconography: ThemeIconography
}

const FAMILY_TRAITS: Record<ThemeFamily, FamilyTraits> = {
  // Horizon — esquinas amables, sombra suave difusa, aire cómodo.
  horizon: {
    shape: { radiusXs: '4px', radiusSm: '8px', radiusMd: '12px', radiusLg: '18px', borderWidth: '1px' },
    elevation: (dark) => ({
      card: dark ? '0 1px 2px rgba(0,0,0,0.5)' : '0 1px 3px rgba(16,40,68,0.08), 0 1px 2px rgba(16,40,68,0.04)',
      raised: dark ? '0 8px 24px rgba(0,0,0,0.55)' : '0 6px 20px rgba(16,40,68,0.12)',
      overlay: dark ? '0 16px 48px rgba(0,0,0,0.6)' : '0 18px 50px rgba(16,40,68,0.20)',
    }),
    motion: { durationFast: '120ms', durationBase: '200ms', easing: 'cubic-bezier(0.2, 0, 0, 1)' },
    typographyBase: 14,
    headingTracking: '-0.01em',
    densityDefault: 'comfortable',
    iconography: { style: 'line', strokeWidth: '1.6' },
  },
  // Quartz — esquinas mínimas, superficies casi planas, contraste alto,
  // más compacto por defecto (Fiori 3).
  quartz: {
    shape: { radiusXs: '2px', radiusSm: '4px', radiusMd: '6px', radiusLg: '8px', borderWidth: '1px' },
    elevation: (dark) => ({
      card: dark ? '0 0 0 1px rgba(255,255,255,0.06)' : '0 0 0 1px rgba(0,0,0,0.06)',
      raised: dark ? '0 4px 16px rgba(0,0,0,0.5)' : '0 2px 10px rgba(0,0,0,0.14)',
      overlay: dark ? '0 12px 40px rgba(0,0,0,0.55)' : '0 10px 34px rgba(0,0,0,0.18)',
    }),
    motion: { durationFast: '80ms', durationBase: '140ms', easing: 'cubic-bezier(0.4, 0, 0.2, 1)' },
    typographyBase: 13,
    headingTracking: '0',
    densityDefault: 'compact',
    iconography: { style: 'line', strokeWidth: '1.4' },
  },
  // Belize — herencia SAP Belize: barras densas, esquinas duras, cabeceras
  // de tabla teñidas, tipografía compacta.
  belize: {
    shape: { radiusXs: '0px', radiusSm: '2px', radiusMd: '3px', radiusLg: '4px', borderWidth: '1px' },
    elevation: (dark) => ({
      card: dark ? '0 0 0 1px rgba(255,255,255,0.05)' : '0 1px 0 rgba(0,0,0,0.10), 0 0 0 1px rgba(0,0,0,0.05)',
      raised: dark ? '0 3px 12px rgba(0,0,0,0.5)' : '0 2px 6px rgba(0,0,0,0.16)',
      overlay: dark ? '0 10px 30px rgba(0,0,0,0.55)' : '0 8px 24px rgba(0,0,0,0.2)',
    }),
    motion: { durationFast: '60ms', durationBase: '120ms', easing: 'cubic-bezier(0.33, 0, 0.2, 1)' },
    typographyBase: 13,
    headingTracking: '0',
    densityDefault: 'compact',
    iconography: { style: 'duotone', strokeWidth: '1.5' },
  },
  // NEXORA — identidad propia: híbrido Horizon (radio) + densidad ejecutiva.
  nexora: {
    shape: { radiusXs: '4px', radiusSm: '6px', radiusMd: '9px', radiusLg: '14px', borderWidth: '1px' },
    elevation: (dark) => ({
      card: dark ? '0 1px 2px rgba(0,0,0,0.45)' : '0 1px 2px rgba(11,39,74,0.10)',
      raised: dark ? '0 8px 22px rgba(0,0,0,0.5)' : '0 6px 18px rgba(11,39,74,0.14)',
      overlay: dark ? '0 16px 44px rgba(0,0,0,0.55)' : '0 16px 44px rgba(11,39,74,0.22)',
    }),
    motion: { durationFast: '110ms', durationBase: '180ms', easing: 'cubic-bezier(0.2, 0, 0, 1)' },
    typographyBase: 14,
    headingTracking: '-0.005em',
    densityDefault: 'comfortable',
    iconography: { style: 'line', strokeWidth: '1.6' },
  },
}

interface PresetInput {
  id: string
  name: string
  description: string
  family: ThemeFamily
  variant: string
  isDark?: boolean
  contrast?: ThemeContrast
  fontFamily?: string
  palette: ThemePalette
  shell: Omit<ThemeShell, 'style'> & { style?: ThemeShell['style'] }
  tables: ThemeTables
  charts: ThemeCharts
  /** Overrides estructurales puntuales (p.ej. Executive usa radio menor). */
  shape?: Partial<ThemeShape>
  densityDefault?: Density
  focusRing?: string
}

function makePreset(input: PresetInput): ThemePreset {
  const traits = FAMILY_TRAITS[input.family]
  const isDark = input.isDark ?? false
  const contrast = input.contrast ?? 'normal'
  return {
    id: input.id,
    name: input.name,
    description: input.description,
    family: input.family,
    variant: input.variant,
    isDark,
    contrast,
    densityDefault: input.densityDefault ?? traits.densityDefault,
    palette: input.palette,
    typography: {
      fontFamily: input.fontFamily ?? INTER,
      fontFamilyMono: MONO,
      baseSize: traits.typographyBase,
      headingWeight: contrast === 'high' ? 800 : 700,
      bodyWeight: 400,
      labelWeight: 600,
      headingTracking: traits.headingTracking,
    },
    shell: { style: input.shell.style ?? (isDark ? 'solid-dark' : 'solid-light'), ...input.shell },
    shape: { ...traits.shape, ...input.shape },
    elevation: traits.elevation(isDark),
    motion: traits.motion,
    tables: input.tables,
    charts: input.charts,
    iconography: traits.iconography,
    focus: {
      ring: input.focusRing ?? input.palette.accent,
      width: contrast === 'high' ? '3px' : '2px',
      offset: '2px',
    },
  }
}

export const THEME_PRESETS: ThemePreset[] = [
  makePreset({
    id: 'nexora-horizon-light',
    name: 'NEXORA Horizon',
    description: 'Tema por defecto: superficies blancas, fondo gris azulado, azul eléctrico. Limpio y denso.',
    family: 'nexora',
    variant: 'horizon-light',
    palette: {
      pageBg: '#eef3f9', surface: '#ffffff', surfaceRaised: '#ffffff', surfaceSunken: '#f4f7fb',
      text: '#102844', textMuted: '#4f6176', textSubtle: '#7c8da6', border: '#dce5ef', borderStrong: '#b9c9dc',
      accent: '#1769d2', accentHover: '#1257ad', accentContrast: '#ffffff',
      positive: '#0f9f6e', negative: '#dc3f50', warning: '#c67c11', info: '#1769d2',
    },
    shell: {
      sidebarBg: '#0b274a', sidebarText: '#c7d7ea', sidebarActiveBg: '#123a68', sidebarActiveText: '#ffffff',
      topbarBg: '#ffffff', topbarText: '#102844', topbarBorder: '#dce5ef',
    },
    tables: { headerBg: '#f4f7fb', headerText: '#4f6176', rowHover: '#f0f5fb', stripe: '#fafcfe', divider: '#e6ecf3' },
    charts: { grid: '#e6ecf3', axis: '#7c8da6', series: ['#1769d2', '#0f9f6e', '#dc3f50', '#c67c11'] },
  }),
  makePreset({
    id: 'nexora-executive',
    name: 'NEXORA Executive',
    description: 'Serio, tipografía compacta, para el comité financiero.',
    family: 'nexora',
    variant: 'executive',
    fontFamily: "'Inter', Georgia, 'Times New Roman', serif",
    shape: { radiusMd: '4px', radiusLg: '6px' },
    densityDefault: 'finance-dense',
    palette: {
      pageBg: '#f2f0ec', surface: '#ffffff', surfaceRaised: '#ffffff', surfaceSunken: '#eae7df',
      text: '#1b1a17', textMuted: '#5a564d', textSubtle: '#8a8578', border: '#ddd8ce', borderStrong: '#c3bcac',
      accent: '#7a5c1e', accentHover: '#5f4715', accentContrast: '#ffffff',
      positive: '#3f7d3f', negative: '#a03030', warning: '#9a6a10', info: '#3a5c8a',
    },
    shell: {
      style: 'solid-dark',
      sidebarBg: '#26241f', sidebarText: '#d9d3c5', sidebarActiveBg: '#3a362d', sidebarActiveText: '#ffffff',
      topbarBg: '#ffffff', topbarText: '#1b1a17', topbarBorder: '#ddd8ce',
    },
    tables: { headerBg: '#eae7df', headerText: '#5a564d', rowHover: '#f2efe9', stripe: '#faf9f6', divider: '#e2ddd2' },
    charts: { grid: '#e2ddd2', axis: '#8a8578', series: ['#7a5c1e', '#3f7d3f', '#a03030', '#3a5c8a'] },
  }),
  makePreset({
    id: 'nexora-dark',
    name: 'NEXORA Dark',
    description: 'Modo oscuro de NEXORA para salas de control.',
    family: 'nexora',
    variant: 'dark',
    isDark: true,
    palette: {
      pageBg: '#0b1220', surface: '#141d2e', surfaceRaised: '#1b2740', surfaceSunken: '#0e1626',
      text: '#e7edf6', textMuted: '#9fb0c6', textSubtle: '#6f8296', border: '#26324a', borderStrong: '#3a4a68',
      accent: '#55a3ff', accentHover: '#7ab8ff', accentContrast: '#04122a',
      positive: '#34d399', negative: '#f87171', warning: '#fbbf24', info: '#55a3ff',
    },
    shell: {
      sidebarBg: '#0a0f1a', sidebarText: '#c7d7ea', sidebarActiveBg: '#152238', sidebarActiveText: '#ffffff',
      topbarBg: '#141d2e', topbarText: '#e7edf6', topbarBorder: '#26324a',
    },
    tables: { headerBg: '#1b2740', headerText: '#9fb0c6', rowHover: '#1a2338', stripe: '#121b2c', divider: '#26324a' },
    charts: { grid: '#26324a', axis: '#6f8296', series: ['#55a3ff', '#34d399', '#f87171', '#fbbf24'] },
  }),
  makePreset({
    id: 'horizon-light',
    name: 'Morning Horizon',
    description: 'Superficies planas, bordes suaves, aire cómodo. Dirección Horizon clara.',
    family: 'horizon',
    variant: 'morning',
    fontFamily: SYSTEM,
    palette: {
      pageBg: '#f5f6f7', surface: '#ffffff', surfaceRaised: '#ffffff', surfaceSunken: '#eef1f4',
      text: '#1d2d3e', textMuted: '#556b82', textSubtle: '#8a9bad', border: '#e5e9ee', borderStrong: '#c8d1db',
      accent: '#0a6ed1', accentHover: '#085aad', accentContrast: '#ffffff',
      positive: '#107e3e', negative: '#bb0000', warning: '#e9730c', info: '#0a6ed1',
    },
    shell: {
      style: 'solid-dark',
      sidebarBg: '#1d2d3e', sidebarText: '#cfd8e3', sidebarActiveBg: '#2b4056', sidebarActiveText: '#ffffff',
      topbarBg: '#ffffff', topbarText: '#1d2d3e', topbarBorder: '#e5e9ee',
    },
    tables: { headerBg: '#eef1f4', headerText: '#556b82', rowHover: '#eff3f7', stripe: '#f9fafb', divider: '#e5e9ee' },
    charts: { grid: '#e5e9ee', axis: '#8a9bad', series: ['#0a6ed1', '#107e3e', '#bb0000', '#e9730c'] },
  }),
  makePreset({
    id: 'horizon-dark',
    name: 'Evening Horizon',
    description: 'Horizon en modo oscuro.',
    family: 'horizon',
    variant: 'evening',
    isDark: true,
    fontFamily: SYSTEM,
    palette: {
      pageBg: '#12171c', surface: '#1c2329', surfaceRaised: '#242c33', surfaceSunken: '#161b20',
      text: '#eaeef2', textMuted: '#a7b4c0', textSubtle: '#788793', border: '#2c353d', borderStrong: '#3f4a54',
      accent: '#4db1ff', accentHover: '#71c2ff', accentContrast: '#0b0f12',
      positive: '#4ade80', negative: '#ff6b6b', warning: '#f7b955', info: '#4db1ff',
    },
    shell: {
      sidebarBg: '#0c1013', sidebarText: '#cfd8e3', sidebarActiveBg: '#1a2228', sidebarActiveText: '#ffffff',
      topbarBg: '#1c2329', topbarText: '#eaeef2', topbarBorder: '#2c353d',
    },
    tables: { headerBg: '#242c33', headerText: '#a7b4c0', rowHover: '#212a31', stripe: '#191f24', divider: '#2c353d' },
    charts: { grid: '#2c353d', axis: '#788793', series: ['#4db1ff', '#4ade80', '#ff6b6b', '#f7b955'] },
  }),
  makePreset({
    id: 'quartz-light',
    name: 'Quartz Light',
    description: 'Aire y contraste alto, esquinas mínimas. Inspirado en Fiori 3 / Quartz.',
    family: 'quartz',
    variant: 'light',
    fontFamily: SYSTEM,
    palette: {
      pageBg: '#fafafa', surface: '#ffffff', surfaceRaised: '#ffffff', surfaceSunken: '#f2f2f2',
      text: '#32363a', textMuted: '#6a6d70', textSubtle: '#8f9296', border: '#e0e0e0', borderStrong: '#c2c2c2',
      accent: '#0854a0', accentHover: '#06427e', accentContrast: '#ffffff',
      positive: '#256f3a', negative: '#aa0808', warning: '#a35b10', info: '#0854a0',
    },
    shell: {
      style: 'solid-light',
      sidebarBg: '#354a5f', sidebarText: '#d9e0e7', sidebarActiveBg: '#45606f', sidebarActiveText: '#ffffff',
      topbarBg: '#ffffff', topbarText: '#32363a', topbarBorder: '#e0e0e0',
    },
    tables: { headerBg: '#f2f2f2', headerText: '#6a6d70', rowHover: '#f4f4f4', stripe: '#fbfbfb', divider: '#e0e0e0' },
    charts: { grid: '#e0e0e0', axis: '#8f9296', series: ['#0854a0', '#256f3a', '#aa0808', '#a35b10'] },
  }),
  makePreset({
    id: 'quartz-dark',
    name: 'Quartz Dark',
    description: 'Quartz en modo oscuro.',
    family: 'quartz',
    variant: 'dark',
    isDark: true,
    fontFamily: SYSTEM,
    palette: {
      pageBg: '#1c1c1c', surface: '#2a2c2e', surfaceRaised: '#35383b', surfaceSunken: '#232425',
      text: '#eaecee', textMuted: '#a9adb0', textSubtle: '#7c8083', border: '#3a3d40', borderStrong: '#4d5154',
      accent: '#5fb0ff', accentHover: '#82c3ff', accentContrast: '#0b0f14',
      positive: '#4ade80', negative: '#ff7a7a', warning: '#f7c04d', info: '#5fb0ff',
    },
    shell: {
      sidebarBg: '#121314', sidebarText: '#d9e0e7', sidebarActiveBg: '#212223', sidebarActiveText: '#ffffff',
      topbarBg: '#2a2c2e', topbarText: '#eaecee', topbarBorder: '#3a3d40',
    },
    tables: { headerBg: '#35383b', headerText: '#a9adb0', rowHover: '#303234', stripe: '#262728', divider: '#3a3d40' },
    charts: { grid: '#3a3d40', axis: '#7c8083', series: ['#5fb0ff', '#4ade80', '#ff7a7a', '#f7c04d'] },
  }),
  makePreset({
    id: 'belize-light',
    name: 'Belize',
    description: 'Herencia SAP Belize: barras densas, esquinas duras, cabeceras de tabla teñidas.',
    family: 'belize',
    variant: 'light',
    fontFamily: SYSTEM,
    palette: {
      pageBg: '#edeff0', surface: '#ffffff', surfaceRaised: '#ffffff', surfaceSunken: '#e6e9ea',
      text: '#33363a', textMuted: '#5b6166', textSubtle: '#89909a', border: '#d1d5d9', borderStrong: '#b0b6bc',
      accent: '#0a6ed1', accentHover: '#085aad', accentContrast: '#ffffff',
      positive: '#107e3e', negative: '#b00', warning: '#df6e0c', info: '#0a6ed1',
    },
    shell: {
      style: 'tinted',
      sidebarBg: '#1c3a52', sidebarText: '#c8d6e2', sidebarActiveBg: '#2a4f6c', sidebarActiveText: '#ffffff',
      topbarBg: '#345c72', topbarText: '#ffffff', topbarBorder: '#2a4f6c',
    },
    tables: { headerBg: '#dfe6ec', headerText: '#33363a', rowHover: '#eef2f5', stripe: '#f7f9fa', divider: '#d1d5d9' },
    charts: { grid: '#d1d5d9', axis: '#89909a', series: ['#0a6ed1', '#107e3e', '#bb0000', '#df6e0c'] },
  }),
  makePreset({
    id: 'belize-deep',
    name: 'Belize Deep',
    description: 'Belize con shell azul profundo y contraste reforzado.',
    family: 'belize',
    variant: 'deep',
    fontFamily: SYSTEM,
    palette: {
      pageBg: '#e8ebed', surface: '#ffffff', surfaceRaised: '#ffffff', surfaceSunken: '#dfe3e6',
      text: '#2b2f33', textMuted: '#525860', textSubtle: '#7f868f', border: '#c8cdd2', borderStrong: '#a6acb3',
      accent: '#08519c', accentHover: '#063f79', accentContrast: '#ffffff',
      positive: '#0b6e37', negative: '#a30000', warning: '#c86200', info: '#08519c',
    },
    shell: {
      style: 'tinted',
      sidebarBg: '#0e2c44', sidebarText: '#bcd0e0', sidebarActiveBg: '#1b425f', sidebarActiveText: '#ffffff',
      topbarBg: '#123c5a', topbarText: '#ffffff', topbarBorder: '#1b425f',
    },
    tables: { headerBg: '#d7e0e7', headerText: '#2b2f33', rowHover: '#e9eef2', stripe: '#f4f7f9', divider: '#c8cdd2' },
    charts: { grid: '#c8cdd2', axis: '#7f868f', series: ['#08519c', '#0b6e37', '#a30000', '#c86200'] },
  }),
  makePreset({
    id: 'high-contrast',
    name: 'Horizon HCB (alto contraste negro)',
    description: 'Fondo negro, texto blanco, bordes definidos. No depende solo del color.',
    family: 'nexora',
    variant: 'hcb',
    isDark: true,
    contrast: 'high',
    fontFamily: SYSTEM,
    shape: { radiusXs: '0px', radiusSm: '0px', radiusMd: '0px', radiusLg: '0px', borderWidth: '2px' },
    palette: {
      pageBg: '#000000', surface: '#000000', surfaceRaised: '#0a0a0a', surfaceSunken: '#000000',
      text: '#ffffff', textMuted: '#f0f0f0', textSubtle: '#e0e0e0', border: '#ffffff', borderStrong: '#ffffff',
      accent: '#ffd500', accentHover: '#ffe34d', accentContrast: '#000000',
      positive: '#3cff8f', negative: '#ff5b5b', warning: '#ffd500', info: '#7ec8ff',
    },
    shell: {
      sidebarBg: '#000000', sidebarText: '#ffffff', sidebarActiveBg: '#1a1a1a', sidebarActiveText: '#ffd500',
      topbarBg: '#000000', topbarText: '#ffffff', topbarBorder: '#ffffff',
    },
    tables: { headerBg: '#0a0a0a', headerText: '#ffffff', rowHover: '#1a1a1a', stripe: '#000000', divider: '#ffffff' },
    charts: { grid: '#ffffff', axis: '#ffffff', series: ['#ffd500', '#3cff8f', '#ff5b5b', '#7ec8ff'] },
    focusRing: '#ffffff',
  }),
  makePreset({
    id: 'high-contrast-white',
    name: 'Horizon HCW (alto contraste blanco)',
    description: 'Fondo blanco, texto negro, bordes definidos. Accesibilidad.',
    family: 'nexora',
    variant: 'hcw',
    contrast: 'high',
    fontFamily: SYSTEM,
    shape: { radiusXs: '0px', radiusSm: '0px', radiusMd: '0px', radiusLg: '0px', borderWidth: '2px' },
    palette: {
      pageBg: '#ffffff', surface: '#ffffff', surfaceRaised: '#ffffff', surfaceSunken: '#f0f0f0',
      text: '#000000', textMuted: '#1a1a1a', textSubtle: '#333333', border: '#000000', borderStrong: '#000000',
      accent: '#0000cc', accentHover: '#0000a0', accentContrast: '#ffffff',
      positive: '#005c1f', negative: '#a30000', warning: '#7a4a00', info: '#0000cc',
    },
    shell: {
      sidebarBg: '#ffffff', sidebarText: '#000000', sidebarActiveBg: '#e6e6e6', sidebarActiveText: '#0000cc',
      topbarBg: '#ffffff', topbarText: '#000000', topbarBorder: '#000000',
    },
    tables: { headerBg: '#f0f0f0', headerText: '#000000', rowHover: '#e6e6e6', stripe: '#ffffff', divider: '#000000' },
    charts: { grid: '#000000', axis: '#000000', series: ['#0000cc', '#005c1f', '#a30000', '#7a4a00'] },
    focusRing: '#000000',
  }),
]

export const DEFAULT_THEME_ID = 'nexora-horizon-light'
export const DEFAULT_DENSITY: Density = 'comfortable'
export const DEFAULT_UI_SCALE: UiScale = 100
export const UI_SCALES: UiScale[] = [90, 100, 110]
export const DENSITIES: Density[] = ['comfortable', 'compact', 'finance-dense']

/** Multiplicador de espaciado/alto de fila por densidad (§8). */
export const DENSITY_SCALE: Record<Density, number> = {
  comfortable: 1,
  compact: 0.78,
  'finance-dense': 0.62,
}

export const DENSITY_LABEL: Record<Density, string> = {
  comfortable: 'Cómoda',
  compact: 'Compacta',
  'finance-dense': 'Finance Dense (máxima densidad de cifras)',
}

export function getThemePreset(id: string | null | undefined): ThemePreset {
  return THEME_PRESETS.find((preset) => preset.id === id) ?? THEME_PRESETS[0]
}

/**
 * Compilador: estructura tipada → variables CSS. Emite tanto los tokens
 * nuevos (`--nx-shape-*`, `--nx-shell-*`, `--nx-elev-*`, `--nx-table-*`,
 * `--nx-chart-*`) como los alias históricos (`--nx-theme-page-bg`,
 * `--nx-theme-accent`, `--nx-theme-radius`, `--nx-theme-font`,
 * `--nx-density-scale`) para que el CSS existente siga funcionando sin
 * reescritura big-bang.
 */
export function compileTheme(
  preset: ThemePreset,
  density: Density = preset.densityDefault,
  scale: UiScale = DEFAULT_UI_SCALE,
): Record<string, string> {
  const p = preset.palette
  const s = preset.shell
  const sh = preset.shape
  const t = preset.typography
  const densityScale = DENSITY_SCALE[density]
  const uiScale = scale / 100

  return {
    // --- Alias históricos (compatibilidad) ---
    '--nx-theme-page-bg': p.pageBg,
    '--nx-theme-surface': p.surface,
    '--nx-theme-surface-2': p.surfaceSunken,
    '--nx-theme-text': p.text,
    '--nx-theme-text-muted': p.textMuted,
    '--nx-theme-border': p.border,
    '--nx-theme-accent': p.accent,
    '--nx-theme-accent-contrast': p.accentContrast,
    '--nx-theme-sidebar-bg': s.sidebarBg,
    '--nx-theme-sidebar-text': s.sidebarText,
    '--nx-theme-radius': sh.radiusMd,
    '--nx-theme-font': t.fontFamily,
    '--nx-density-scale': String(densityScale),

    // --- Paleta estructurada ---
    '--nx-color-page-bg': p.pageBg,
    '--nx-color-surface': p.surface,
    '--nx-color-surface-raised': p.surfaceRaised,
    '--nx-color-surface-sunken': p.surfaceSunken,
    '--nx-color-text': p.text,
    '--nx-color-text-muted': p.textMuted,
    '--nx-color-text-subtle': p.textSubtle,
    '--nx-color-border': p.border,
    '--nx-color-border-strong': p.borderStrong,
    '--nx-color-accent': p.accent,
    '--nx-color-accent-hover': p.accentHover,
    '--nx-color-accent-contrast': p.accentContrast,
    '--nx-color-positive': p.positive,
    '--nx-color-negative': p.negative,
    '--nx-color-warning': p.warning,
    '--nx-color-info': p.info,

    // --- Tipografía ---
    '--nx-font-family': t.fontFamily,
    '--nx-font-mono': t.fontFamilyMono,
    '--nx-font-base-size': `${(t.baseSize * uiScale).toFixed(2)}px`,
    '--nx-font-weight-heading': String(t.headingWeight),
    '--nx-font-weight-body': String(t.bodyWeight),
    '--nx-font-weight-label': String(t.labelWeight),
    '--nx-heading-tracking': t.headingTracking,

    // --- Shell ---
    '--nx-shell-style': s.style,
    '--nx-shell-sidebar-bg': s.sidebarBg,
    '--nx-shell-sidebar-text': s.sidebarText,
    '--nx-shell-sidebar-active-bg': s.sidebarActiveBg,
    '--nx-shell-sidebar-active-text': s.sidebarActiveText,
    '--nx-shell-topbar-bg': s.topbarBg,
    '--nx-shell-topbar-text': s.topbarText,
    '--nx-shell-topbar-border': s.topbarBorder,

    // --- Forma / elevación / movimiento ---
    '--nx-shape-radius-xs': sh.radiusXs,
    '--nx-shape-radius-sm': sh.radiusSm,
    '--nx-shape-radius-md': sh.radiusMd,
    '--nx-shape-radius-lg': sh.radiusLg,
    '--nx-shape-border-width': sh.borderWidth,
    '--nx-elev-card': preset.elevation.card,
    '--nx-elev-raised': preset.elevation.raised,
    '--nx-elev-overlay': preset.elevation.overlay,
    '--nx-motion-fast': preset.motion.durationFast,
    '--nx-motion-base': preset.motion.durationBase,
    '--nx-motion-easing': preset.motion.easing,

    // --- Tablas ---
    '--nx-table-header-bg': preset.tables.headerBg,
    '--nx-table-header-text': preset.tables.headerText,
    '--nx-table-row-hover': preset.tables.rowHover,
    '--nx-table-stripe': preset.tables.stripe,
    '--nx-table-divider': preset.tables.divider,

    // --- Charts ---
    '--nx-chart-grid': preset.charts.grid,
    '--nx-chart-axis': preset.charts.axis,
    '--nx-chart-series-1': preset.charts.series[0],
    '--nx-chart-series-2': preset.charts.series[1],
    '--nx-chart-series-3': preset.charts.series[2],
    '--nx-chart-series-4': preset.charts.series[3],

    // --- Iconografía / foco ---
    '--nx-icon-stroke': preset.iconography.strokeWidth,
    '--nx-focus-ring': preset.focus.ring,
    '--nx-focus-width': preset.focus.width,
    '--nx-focus-offset': preset.focus.offset,

    // --- Densidad / escala ---
    '--nx-density-row-height': `${(38 * densityScale * uiScale).toFixed(1)}px`,
    '--nx-density-control-height': `${(36 * densityScale * uiScale).toFixed(1)}px`,
    '--nx-density-gap': `${(12 * densityScale).toFixed(1)}px`,
    '--nx-density-card-padding': `${(16 * densityScale).toFixed(1)}px`,
    '--nx-ui-scale': String(uiScale),
  }
}
