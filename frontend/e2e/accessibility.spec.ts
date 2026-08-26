import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'

/**
 * NXR-REQ-0105 (Accessibility, WCAG AA). Real automated audit
 * (axe-core, the actual "herramienta" the traceability row asked for)
 * against real authenticated pages -- same backend+frontend
 * `playwright.config.ts` starts for `critical-journey.spec.ts` (own DB
 * `nexora_e2e`, own ports). A screen-reader pass (VoiceOver/NVDA) is a
 * genuinely separate, human-only gap this suite cannot close --
 * documented honestly in `frontend/e2e/README.md`, not skipped
 * silently.
 */

const ADMIN_EMAIL = 'admin@nexora.group'
const ADMIN_PASSWORD = 'NexoraAdmin123!'

async function scan(page: import('@playwright/test').Page) {
  return new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
}

function formatViolations(results: Awaited<ReturnType<typeof scan>>): string {
  return results.violations
    .map(
      (v) =>
        `${v.id} (${v.impact}): ${v.help}\n${v.nodes.map((n) => `  - ${n.target.join(' ')}`).join('\n')}`,
    )
    .join('\n\n')
}

test.describe.configure({ mode: 'serial' })

test.describe('Accessibility (WCAG AA)', () => {
  test('login page has no WCAG A/AA violations', async ({ page }) => {
    await page.goto('/login')
    const results = await scan(page)
    expect(results.violations, formatViolations(results)).toEqual([])
  })

  test('authenticated app shell + key screens have no WCAG A/AA violations', async ({ page }) => {
    await page.goto('/login')
    await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
    await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()
    await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })

    const routes = [
      '/inicio',
      '/proyectos',
      '/finanzas/tesoreria',
      '/finanzas/contabilidad',
      '/control/reportes',
      '/control/auditoria',
    ]

    for (const route of routes) {
      await page.goto(route)
      const results = await scan(page)
      expect(results.violations, `${route}:\n${formatViolations(results)}`).toEqual([])
    }
  })
})
