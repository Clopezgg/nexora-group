import { describe, expect, it } from 'vitest'
import { DEFAULT_THEME_ID, THEME_PRESETS, getThemePreset } from '../src/theme/themes'
import { formatMoney } from '../src/utils/currency'

describe('Theme Engine — §68: solo presentación', () => {
  it('cada preset solo define variables CSS (nada lógico)', () => {
    for (const preset of THEME_PRESETS) {
      for (const key of Object.keys(preset.vars)) {
        expect(key.startsWith('--nx-theme-')).toBe(true)
      }
    }
  })

  it('hay al menos 9 presets, incluyendo oscuros y alto contraste', () => {
    expect(THEME_PRESETS.length).toBeGreaterThanOrEqual(9)
    expect(THEME_PRESETS.some((p) => p.isDark)).toBe(true)
    expect(THEME_PRESETS.some((p) => p.id === 'high-contrast')).toBe(true)
  })

  it('getThemePreset cae en NEXORA Classic ante un id desconocido', () => {
    expect(getThemePreset('no-existe').id).toBe(DEFAULT_THEME_ID)
    expect(getThemePreset(null).id).toBe(DEFAULT_THEME_ID)
  })

  it('el formato de dinero es idéntico bajo cualquier preset (no depende del tema)', () => {
    const baseline = formatMoney(150000, 'HNL')
    for (const preset of THEME_PRESETS) {
      // Aplicar el preset a :root no debe cambiar el formateo (es puro CSS).
      for (const [k, v] of Object.entries(preset.vars)) {
        document.documentElement.style.setProperty(k, v)
      }
      expect(formatMoney(150000, 'HNL')).toBe(baseline)
    }
  })
})
