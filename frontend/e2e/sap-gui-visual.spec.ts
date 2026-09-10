import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

/**
 * Baselines visuales SAP GUI: 4 variantes × 3 viewports en páginas densas.
 * Gates duros por captura: sin overflow horizontal, sin errores de consola o
 * de página, sin requests 500. Las capturas quedan en `e2e/visual/` como
 * artefactos estables (no toHaveScreenshot: los datos son vivos y el gate
 * es estructural, no pixel-perfect).
 */

const VARIANTS = ['sap-gui-signature', 'sap-gui-tradeshow', 'sap-gui-horizon', 'sap-gui-horizon-dark'] as const
const VIEWPORTS = [
  { name: '1440', width: 1440, height: 900 },
  { name: '768', width: 768, height: 1024 },
  { name: '390', width: 390, height: 844 },
] as const
const PAGES = [
  { path: '/control/configuracion', name: 'configuracion' },
  { path: '/inicio', name: 'inicio' },
  { path: '/finanzas/tesoreria', name: 'tesoreria' },
  { path: '/finanzas/cuentas-por-pagar', name: 'cuentas-por-pagar' },
] as const

async function login(page: Page) {
  await page.goto('/login')
  await page.getByLabel('Correo electrónico').fill('admin@nexora.group')
  await page.getByLabel('Contraseña').fill('NexoraAdmin123!')
  await page.getByRole('button', { name: /iniciar sesión/i }).click()
  await expect(page).toHaveURL(/\/inicio/)
}

async function ensureCompany(request: APIRequestContext) {
  const existing = await request.get('/api/master-data/companies')
  if (existing.ok() && ((await existing.json()) as unknown[]).length > 0) return
  await request.post('/api/master-data/companies', {
    data: { name: 'Compañía visual SAP GUI', functionalCurrencyCode: 'HNL' },
  })
}

async function setTheme(page: Page, themeId: string) {
  await page.goto('/control/configuracion')
  await page.getByLabel('Familia').selectOption('sap-gui')
  const confirmBtn = page.getByRole('button', { name: 'Cambiar a SAP GUI' })
  if (await confirmBtn.isVisible().catch(() => false)) {
    await page.getByRole('dialog', { name: 'Cambiar a SAP GUI' }).waitFor()
    await confirmBtn.click()
    await expect(page.locator('html')).toHaveAttribute('data-nx-family', 'sap-gui')
  }
  await page.getByLabel('Variante').selectOption(themeId)
  await expect(page.locator('html')).toHaveAttribute('data-nx-theme', themeId)
  await page.getByRole('button', { name: 'Guardar como mi preferencia' }).click()
  await page.reload()
  await expect.poll(() => page.locator('html').getAttribute('data-nx-theme')).toBe(themeId)
}

async function unlockProtectedEdit(page: Page) {
  await page.getByRole('button', { name: 'Edición protegida' }).click()
  const dialog = page.getByRole('dialog', { name: 'Desbloquear edición' })
  await dialog.getByLabel('Token de seguridad').fill(process.env.E2E_EDIT_ACCESS_TOKEN!)
  await dialog.getByRole('button', { name: 'Desbloquear', exact: true }).click()
  await expect(dialog).not.toBeVisible()
}

test('SAP GUI visual baselines', async ({ page }) => {
  await login(page)
  await unlockProtectedEdit(page)
  await ensureCompany(page.request)

  for (const variant of VARIANTS) {
    await setTheme(page, variant)
    for (const viewport of VIEWPORTS) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height })
      for (const { path, name } of PAGES) {
        const consoleErrors: string[] = []
        const pageErrors: string[] = []
        const failedRequests: string[] = []
        page.on('console', (message) => {
          if (message.type() === 'error') consoleErrors.push(message.text())
        })
        page.on('pageerror', (error) => pageErrors.push(String(error)))
        page.on('response', (response) => {
          if (response.status() >= 500) failedRequests.push(`${response.status()} ${response.url()}`)
        })

        await page.goto(path)
        await expect(page.locator('main')).toBeVisible()
        await expect(page.locator('body')).not.toContainText('Application error')
        const overflow = await page.evaluate(() => ({
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
        }))
        expect(overflow.scrollWidth, `${variant} ${viewport.name} ${path}: sin overflow`).toBeLessThanOrEqual(
          overflow.clientWidth + 1,
        )
        await page.screenshot({ path: `e2e/visual/sap-${variant}-${viewport.name}-${name}.png` })
        expect(consoleErrors, `${variant} ${viewport.name} ${path}: consola limpia`).toEqual([])
        expect(pageErrors, `${variant} ${viewport.name} ${path}: sin pageerror`).toEqual([])
        expect(failedRequests, `${variant} ${viewport.name} ${path}: sin 500`).toEqual([])
      }
    }
  }
})
