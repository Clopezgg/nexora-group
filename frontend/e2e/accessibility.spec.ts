import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

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
const acceptanceWidths = [1440, 1280, 1024, 768, 430, 390, 360]

async function scan(page: Page) {
  return new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
}

async function expectNoDocumentOverflow(page: Page, label: string) {
  const dimensions = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(
    dimensions.scrollWidth,
    `${label}: document overflow ${dimensions.scrollWidth}px > ${dimensions.clientWidth}px`,
  ).toBeLessThanOrEqual(dimensions.clientWidth + 1)
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

test.describe('Accessibility and responsive acceptance', () => {
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

  test('login and critical modules remain usable at all acceptance widths', async ({ page }) => {
    for (const width of acceptanceWidths) {
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/login')
      await expect(page.getByRole('heading', { name: 'Bienvenido a NEXORA' })).toBeVisible()
      await expect(page.getByLabel('Correo electrónico')).toBeVisible()
      await expect(page.getByLabel('Contraseña')).toBeVisible()
      await expect(page.getByRole('button', { name: 'Iniciar sesión' })).toBeVisible()
      await expectNoDocumentOverflow(page, `login @ ${width}px`)
    }

    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto('/login')
    await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
    await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()
    await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })

    const criticalRoutes = [
      '/inicio',
      '/finanzas/tesoreria',
      '/finanzas/cuentas-por-pagar',
      '/proyectos',
      '/proyectos/presupuestos',
      '/control/reportes',
    ]

    for (const width of acceptanceWidths) {
      await page.setViewportSize({ width, height: 900 })
      for (const route of criticalRoutes) {
        await page.goto(route)
        await expect(page.locator('.nx-app-shell')).toBeVisible()
        if (width <= 1024) {
          // Móvil: el "Salir" ya no vive permanente en la cabecera (§12); la
          // sesión se cierra desde el drawer.
          await expect(page.getByRole('button', { name: 'Abrir navegación' })).toBeVisible()
        } else {
          await expect(page.getByRole('button', { name: 'Cerrar sesión' })).toBeVisible()
        }
        await expectNoDocumentOverflow(page, `${route} @ ${width}px`)
      }
    }

    // El cierre de sesión sigue alcanzable en móvil: dentro del drawer.
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/inicio')
    await page.getByRole('button', { name: 'Abrir navegación' }).click()
    const drawer = page.getByRole('dialog', { name: 'Navegación' })
    await expect(drawer.getByRole('button', { name: 'Cerrar sesión' })).toBeVisible()
  })
})
