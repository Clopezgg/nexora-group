import { describe, expect, it } from 'vitest'
import {
  compileTheme,
  DEFAULT_THEME_ID,
  DENSITIES,
  DENSITY_SCALE,
  getThemePreset,
  THEME_PRESETS,
} from '../src/theme/themes'
import { formatMoney } from '../src/utils/currency'

// Ratio de contraste WCAG entre dos colores hex (#rrggbb).
function contrastRatio(hexA: string, hexB: string): number {
  const lum = (hex: string) => {
    const n = hex.replace('#', '')
    const rgb = [0, 2, 4].map((i) => parseInt(n.slice(i, i + 2), 16) / 255)
    const lin = rgb.map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
  }
  const a = lum(hexA)
  const b = lum(hexB)
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)
}

describe('Enterprise Theme Architecture (§8-§11, §20)', () => {
  it('un ThemePreset ya NO es únicamente Record<string,string> — tiene dominio tipado', () => {
    for (const preset of THEME_PRESETS) {
      expect(typeof preset.palette).toBe('object')
      expect(typeof preset.typography).toBe('object')
      expect(typeof preset.shell).toBe('object')
      expect(typeof preset.shape).toBe('object')
      expect(typeof preset.elevation).toBe('object')
      expect(typeof preset.tables).toBe('object')
      expect(typeof preset.charts).toBe('object')
      expect(Array.isArray(preset.charts.series)).toBe(true)
      // ya no existe un campo `vars` plano como modelo principal
      expect((preset as unknown as { vars?: unknown }).vars).toBeUndefined()
    }
  })

  it('Density incluye Finance Dense y su escala es la más compacta', () => {
    expect(DENSITIES).toContain('finance-dense')
    expect(DENSITY_SCALE['finance-dense']).toBeLessThan(DENSITY_SCALE.compact)
    expect(DENSITY_SCALE.compact).toBeLessThan(DENSITY_SCALE.comfortable)
  })

  it('la UI Scale 90/100/110 cambia el tamaño base de fuente', () => {
    const preset = getThemePreset(DEFAULT_THEME_ID)
    const at90 = compileTheme(preset, 'comfortable', 90)['--nx-font-base-size']
    const at100 = compileTheme(preset, 'comfortable', 100)['--nx-font-base-size']
    const at110 = compileTheme(preset, 'comfortable', 110)['--nx-font-base-size']
    expect(parseFloat(at90)).toBeLessThan(parseFloat(at100))
    expect(parseFloat(at100)).toBeLessThan(parseFloat(at110))
  })

  it('Morning Horizon, Quartz y Belize difieren ESTRUCTURALMENTE, no solo en color', () => {
    const horizon = getThemePreset('horizon-light')
    const quartz = getThemePreset('quartz-light')
    const belize = getThemePreset('belize-light')

    // Radio de esquina distinto por familia.
    const radii = [horizon.shape.radiusMd, quartz.shape.radiusMd, belize.shape.radiusMd]
    expect(new Set(radii).size).toBe(3)

    // Tratamiento de shell distinto.
    expect(new Set([horizon.shell.style, quartz.shell.style, belize.shell.style]).size).toBeGreaterThanOrEqual(2)

    // Elevación de card distinta (sombra difusa vs. borde plano vs. línea).
    expect(new Set([horizon.elevation.card, quartz.elevation.card, belize.elevation.card]).size).toBe(3)

    // Densidad por defecto distinta (Horizon cómoda, Quartz/Belize compacta).
    expect(horizon.densityDefault).toBe('comfortable')
    expect(quartz.densityDefault).toBe('compact')

    // El compilador propaga esas diferencias a variables CSS.
    const hv = compileTheme(horizon)
    const qv = compileTheme(quartz)
    expect(hv['--nx-shape-radius-md']).not.toBe(qv['--nx-shape-radius-md'])
    expect(hv['--nx-elev-card']).not.toBe(qv['--nx-elev-card'])
  })

  it('los temas de alto contraste cumplen 7:1 texto/fondo (WCAG AAA)', () => {
    for (const id of ['high-contrast', 'high-contrast-white']) {
      const preset = getThemePreset(id)
      expect(preset.contrast).toBe('high')
      expect(contrastRatio(preset.palette.text, preset.palette.pageBg)).toBeGreaterThanOrEqual(7)
      expect(contrastRatio(preset.palette.text, preset.palette.surface)).toBeGreaterThanOrEqual(7)
    }
  })

  it('todo tema normal cumple 4.5:1 texto/superficie (WCAG AA)', () => {
    for (const preset of THEME_PRESETS) {
      expect(
        contrastRatio(preset.palette.text, preset.palette.surface),
        `${preset.id}: texto sobre surface`,
      ).toBeGreaterThanOrEqual(4.5)
    }
  })

  it('el default sigue siendo NEXORA Horizon y es el primer preset', () => {
    expect(DEFAULT_THEME_ID).toBe('nexora-horizon-light')
    expect(THEME_PRESETS[0].id).toBe(DEFAULT_THEME_ID)
    expect(getThemePreset('no-existe').id).toBe(DEFAULT_THEME_ID)
    expect(getThemePreset(null).id).toBe(DEFAULT_THEME_ID)
  })

  it('el formato de dinero es idéntico bajo cualquier preset (el tema es puro CSS, §68)', () => {
    const baseline = formatMoney(150000, 'HNL')
    for (const preset of THEME_PRESETS) {
      for (const [k, v] of Object.entries(compileTheme(preset))) {
        document.documentElement.style.setProperty(k, v)
      }
      expect(formatMoney(150000, 'HNL')).toBe(baseline)
    }
  })
})
