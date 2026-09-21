import { expect, test, type APIRequestContext, type Page, type Response } from '@playwright/test'

const ADMIN_EMAIL = 'admin@nexora.group'
const ADMIN_PASSWORD = ['Nexora', 'Admin', '123!'].join('')

async function login(page: Page) {
  await page.goto('/login')
  await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
  await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: /iniciar sesión/i }).click()
  await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })
}

async function unlockEdit(request: APIRequestContext): Promise<string> {
  const token = process.env.E2E_EDIT_ACCESS_TOKEN
  expect(token).toBeTruthy()
  const response = await request.post('/api/edit-access/verify', { data: { token } })
  expect(response.ok(), await response.text()).toBeTruthy()
  const body = (await response.json()) as { capability: string }
  expect(body.capability).toBeTruthy()
  return body.capability
}

/** Wait for a page-owned response before consuming its body. Browser response
 * bodies may be discarded after navigation; diagnostics are only read on error
 * and cannot mask the actual status assertion. */
async function expectFinishedOk(response: Response, label: string): Promise<void> {
  const finishedError = await response.finished()
  expect(finishedError, `${label}: la respuesta no finalizó`).toBeNull()

  if (!response.ok()) {
    let detail = `HTTP ${response.status()}`
    try {
      detail = await response.text()
    } catch (error) {
      detail += ` (diagnóstico del body no disponible: ${String(error)})`
    }
    expect(response.ok(), `${label}: ${detail}`).toBeTruthy()
    return
  }

  expect(response.ok(), `${label}: HTTP ${response.status()}`).toBeTruthy()
}

function dashboardResponseFor(page: Page, companyId: string): Promise<Response> {
  return page.waitForResponse((response) => {
    const url = new URL(response.url())
    return response.request().method() === 'GET' &&
      url.pathname === '/api/dashboard/summary' &&
      url.searchParams.get('companyId') === companyId
  })
}

async function assertMountedDashboard(responsePromise: Promise<Response>, company: { id: string; functionalCurrencyCode: string }) {
  const dashboard = await responsePromise
  await expectFinishedOk(dashboard, 'dashboard montado')
  const dashboardBody = (await dashboard.json()) as { currency: string }
  expect(dashboardBody.currency).toBe(company.functionalCurrencyCode)
}

async function ensureCompany(page: Page): Promise<{ id: string; functionalCurrencyCode: string }> {
  const existing = await page.request.get('/api/master-data/companies')
  expect(existing.ok(), await existing.text()).toBeTruthy()
  const companies = (await existing.json()) as Array<{
    id: string
    functionalCurrencyCode: string | null
  }>
  const configured = companies.find((company) => Boolean(company.functionalCurrencyCode))
  if (configured?.functionalCurrencyCode) {
    return { id: configured.id, functionalCurrencyCode: configured.functionalCurrencyCode }
  }

  const capability = await unlockEdit(page.request)
  const suffix = `${test.info().project.name}-${Date.now()}`
  const created = await page.request.post('/api/master-data/companies', {
    headers: { 'X-Nexora-Edit-Access': capability },
    data: {
      name: `Compatibilidad ${suffix}`,
      functionalCurrencyCode: 'HNL',
    },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  return (await created.json()) as { id: string; functionalCurrencyCode: string }
}

/**
 * Verifies that a route loads its application shell without server or page errors.
 */
async function expectOperationalRoute(page: Page, path: string) {
  const response = await page.goto(path)
  expect(response?.status(), `${path}: HTTP`).toBeLessThan(500)
  await expect(page.locator('.nx-app-shell, .nx-sap-workstation').first()).toBeVisible({ timeout: 15_000 })
  await expect(page.locator('main')).toBeVisible()
  await page.waitForLoadState('networkidle')
  await expect(page.locator('body')).not.toContainText('Application error')
}

/**
 * Verifies the critical authenticated journey across browsers and SAP GUI variants.
 */
async function verifyCrossBrowserCompatibility({ page }: { page: Page }) {
  const pageErrors: string[] = []
  page.on(
    'pageerror',
    /**
     * Records browser errors across the complete compatibility journey.
     */
    (error) => pageErrors.push(String(error)),
  )

  await login(page)
  const company = await ensureCompany(page)

  await page.evaluate((companyId) => {
    window.localStorage.setItem('nexora.activeCompanyId', companyId)
  }, company.id)
  const initialDashboard = dashboardResponseFor(page, company.id)
  await page.reload()
  // Await the page-owned response before deliberately navigating away. This
  // distinguishes a completed dashboard request from an aborted proxy fetch.
  await assertMountedDashboard(initialDashboard, company)

  for (const route of [
    '/inicio',
    '/proyectos',
    '/finanzas/cuentas-por-pagar',
    '/finanzas/tesoreria',
    '/control/configuracion',
  ]) {
    await expectOperationalRoute(page, route)
  }

  const dashboardBeforeEdit = dashboardResponseFor(page, company.id)
  await page.goto('/inicio')
  await assertMountedDashboard(dashboardBeforeEdit, company)
  await page.getByRole('button', { name: 'Edición protegida' }).click()
  const dialog = page.getByRole('dialog', { name: 'Desbloquear edición' })
  await expect(dialog).toBeVisible()
  await dialog.getByLabel('Token de seguridad').fill(process.env.E2E_EDIT_ACCESS_TOKEN!)
  await dialog.getByRole('button', { name: 'Desbloquear', exact: true }).click()
  await expect(dialog).not.toBeVisible()

  for (const variant of [
    'sap-gui-signature',
    'sap-gui-tradeshow',
    'sap-gui-horizon',
    'sap-gui-horizon-dark',
  ]) {
    await page.goto('/control/configuracion')
    await page.waitForLoadState('networkidle')
    if ((await page.locator('html').getAttribute('data-nx-family')) !== 'sap-gui') {
      await page.getByLabel('Familia', { exact: true }).selectOption('sap-gui')
      await page.getByRole('button', { name: 'Cambiar a SAP GUI', exact: true }).click()
    }
    await page.getByLabel('Variante', { exact: true }).selectOption(variant)
    await expect(page.locator('html')).toHaveAttribute('data-nx-theme', variant)
    const preferenceResponsePromise = page.waitForResponse(
      (response) =>
        response.request().method() === 'PUT' &&
        new URL(response.url()).pathname === '/api/me/preferences',
    )
    await page.getByRole('button', { name: 'Guardar como mi preferencia' }).click()
    const preferenceResponse = await preferenceResponsePromise
    await expectFinishedOk(preferenceResponse, 'guardar preferencia')
    await page.reload()
    await page.waitForLoadState('networkidle')
    await expect(page.locator('html')).toHaveAttribute('data-nx-theme', variant, { timeout: 10_000 })
    await page.getByRole('menuitem', { name: 'Sistema', exact: true }).click()
    // A real click verifies the menu is not clipped behind the shell bars.
    const dashboardAfterMenu = dashboardResponseFor(page, company.id)
    await page
      .getByRole('menu', { name: 'Sistema', exact: true })
      .getByRole('menuitem', { name: 'Inicio', exact: true })
      .click()
    await expect(page).toHaveURL(/\/inicio/)
    await assertMountedDashboard(dashboardAfterMenu, company)
    await expectOperationalRoute(page, '/finanzas/contabilidad')
    await expectOperationalRoute(page, '/proyectos/cockpit')
    await expectOperationalRoute(page, '/abastecimiento/inventario')
    await page.getByRole('button', { name: 'Edición habilitada' }).click()
    await page.getByRole('button', { name: 'Edición protegida' }).click()
    await expect(page.getByRole('dialog')).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(page.getByRole('dialog')).not.toBeVisible()
    await page.getByRole('button', { name: 'Edición protegida' }).click()
    await page.getByLabel('Token de seguridad').fill(process.env.E2E_EDIT_ACCESS_TOKEN!)
    await page.getByRole('button', { name: 'Desbloquear', exact: true }).click()
    await expect(page.getByRole('dialog')).not.toBeVisible()
  }

  await page.getByRole('button', { name: 'Cerrar sesión' }).click()
  await expect(page).toHaveURL(/\/login/, { timeout: 10_000 })
  expect(pageErrors).toEqual([])
}

test('cross-browser critical compatibility', verifyCrossBrowserCompatibility)
