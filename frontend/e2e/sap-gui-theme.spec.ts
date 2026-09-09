import AxeBuilder from '@axe-core/playwright'
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

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
  const created = await request.post('/api/master-data/companies', {
    data: { name: 'Compañía de prueba SAP GUI', functionalCurrencyCode: 'HNL' },
  })
  expect(created.ok(), `crear compañía -> ${created.status()}`).toBeTruthy()
}

function formatViolations(results: Awaited<ReturnType<AxeBuilder['analyze']>>) {
  return results.violations
    .map((violation) => `${violation.id}: ${violation.nodes.map((node) => node.target.join(' ')).join(', ')}`)
    .join('\n')
}

async function setTheme(page: Page, themeId: string) {
  const result = await page.evaluate(async (id) => {
    const capability = window.sessionStorage.getItem('nexora.edit-access.capability')
    const response = await fetch('/api/me/preferences', {
      method: 'PUT',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(capability ? { 'X-Nexora-Edit-Access': capability } : {}),
      },
      body: JSON.stringify({ themeId: id, density: 'compact' }),
    })
    return { ok: response.ok, status: response.status, body: await response.text() }
  }, themeId)
  expect(result.ok, `PUT preferencias -> ${result.status}: ${result.body}`).toBeTruthy()
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

test('SAP GUI confirmation, variants and representative routes use one global shell', async ({ page }) => {
  await login(page)
  await unlockProtectedEdit(page)
  await ensureCompany(page.request)
  await page.goto('/control/configuracion')

  await page.getByLabel('Familia').selectOption('sap-gui')
  await expect(page.getByRole('dialog', { name: 'Cambiar a SAP GUI' })).toBeVisible()
  await expect(page.locator('html')).not.toHaveAttribute('data-nx-family', 'sap-gui')
  await page.getByRole('button', { name: 'Cambiar a SAP GUI' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-nx-theme', 'sap-gui-signature')
  await expect(page.getByRole('menubar', { name: 'Barra de menús SAP GUI' })).toBeVisible()
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
    .analyze()
  expect(accessibility.violations, formatViolations(accessibility)).toEqual([])

  await page.getByLabel('Variante').selectOption('sap-gui-tradeshow')
  await expect(page.getByRole('dialog', { name: 'Cambiar a SAP GUI' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Guardar como mi preferencia' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-nx-sap-variant', 'tradeshow')

  const routes = [
    '/inicio',
    '/finanzas/control',
    '/finanzas/tesoreria',
    '/finanzas/cuentas-por-pagar',
    '/proyectos',
    '/abastecimiento/solicitudes',
    '/recursos/personal',
    '/recursos/equipos',
    '/control/documentos',
    '/control/reportes',
    '/control/configuracion',
  ]
  for (const route of routes) {
    await page.goto(route)
    await expect(page.locator('main')).toBeVisible()
    await expect(page.getByRole('banner', { name: 'Barra de herramientas SAP GUI' })).toBeVisible()
    await expect(page.getByRole('status', { name: 'Contexto SAP GUI' })).toBeVisible()
    await expect(page.locator('body')).not.toContainText('Application error')
  }

  await setTheme(page, 'sap-gui-signature')
  await expect(page.locator('html')).toHaveAttribute('data-nx-sap-variant', 'signature')
  await expect(page.getByRole('tree', { name: 'Navegación principal' })).toBeVisible()

  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('button', { name: 'Abrir navegación' })).toBeVisible()
  await page.getByRole('button', { name: 'Abrir navegación' }).click()
  await expect(page.getByRole('dialog', { name: 'Navegación' })).toBeVisible()
  const viewport = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(viewport.scrollWidth).toBeLessThanOrEqual(viewport.clientWidth + 1)
})

test('a modern family never mounts SAP GUI chrome', async ({ page }) => {
  await login(page)
  await unlockProtectedEdit(page)
  await ensureCompany(page.request)
  await setTheme(page, 'quartz-light')
  await expect(page.getByRole('menubar', { name: 'Barra de menús SAP GUI' })).toHaveCount(0)
  await expect(page.getByRole('status', { name: 'Contexto SAP GUI' })).toHaveCount(0)
})
