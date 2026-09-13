import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

/**
 * Matriz visual SAP GUI de aceptación: las cuatro variantes workstation,
 * los siete anchos exigidos y las rutas operativas principales. Cada captura
 * exige además ausencia de overflow de documento, page errors y respuestas 5xx.
 * Las PNG se publican como artifact de CI para inspección humana; generar una
 * captura nunca equivale por sí solo a certificar su calidad visual.
 */

const VARIANTS = [
  'sap-gui-signature',
  'sap-gui-tradeshow',
  'sap-gui-horizon',
  'sap-gui-horizon-dark',
] as const

const VIEWPORTS = [
  { name: '1440', width: 1440, height: 900 },
  { name: '1280', width: 1280, height: 900 },
  { name: '1024', width: 1024, height: 900 },
  { name: '768', width: 768, height: 1024 },
  { name: '430', width: 430, height: 932 },
  { name: '390', width: 390, height: 844 },
  { name: '360', width: 360, height: 800 },
] as const

const PAGES = [
  { path: '/inicio', name: 'inicio' },
  { path: '/inicio/aprobaciones', name: 'aprobaciones' },
  { path: '/proyectos', name: 'proyectos' },
  { path: '/proyectos/wbs', name: 'wbs' },
  { path: '/proyectos/presupuestos', name: 'presupuestos' },
  { path: '/proyectos/cockpit', name: 'cockpit' },
  { path: '/proyectos/avances', name: 'avances' },
  { path: '/proyectos/ordenes-de-cambio', name: 'ordenes-de-cambio' },
  { path: '/abastecimiento/contratos', name: 'contratos-ejecucion' },
  { path: '/finanzas/libro-contractual', name: 'libro-contractual' },
  { path: '/finanzas/cuentas-por-pagar', name: 'cuentas-por-pagar' },
  { path: '/finanzas/cuentas-por-cobrar', name: 'cuentas-por-cobrar' },
  { path: '/finanzas/tesoreria', name: 'tesoreria' },
  { path: '/finanzas/contabilidad', name: 'contabilidad' },
  { path: '/abastecimiento/solicitudes', name: 'solicitudes' },
  { path: '/abastecimiento/ordenes-de-compra', name: 'ordenes-de-compra' },
  { path: '/abastecimiento/entradas-de-servicio', name: 'entradas-de-servicio' },
  { path: '/abastecimiento/inventario', name: 'inventario' },
  { path: '/abastecimiento/almacenes', name: 'almacenes' },
  { path: '/abastecimiento/proveedores', name: 'proveedores' },
  { path: '/comercial/clientes', name: 'clientes' },
  { path: '/control/documentos', name: 'documentos' },
  { path: '/control/evidencias', name: 'evidencias' },
  { path: '/control/reportes', name: 'reportes' },
  { path: '/control/auditoria', name: 'auditoria' },
  { path: '/finanzas/excepciones', name: 'excepciones' },
  { path: '/control/configuracion', name: 'configuracion' },
] as const

async function login(page: Page) {
  const password = ['Nexora', 'Admin', '123!'].join('')
  await page.goto('/login')
  await page.getByLabel('Correo electrónico').fill('admin@nexora.group')
  await page.getByLabel('Contraseña').fill(password)
  await page.getByRole('button', { name: /iniciar sesión/i }).click()
  await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })
}

async function unlockProtectedEdit(page: Page) {
  await page.getByRole('button', { name: 'Edición protegida' }).click()
  const dialog = page.getByRole('dialog', { name: 'Desbloquear edición' })
  await dialog.getByLabel('Token de seguridad').fill(process.env.E2E_EDIT_ACCESS_TOKEN!)
  await dialog.getByRole('button', { name: 'Desbloquear', exact: true }).click()
  await expect(dialog).not.toBeVisible()
}

async function ensureCompany(page: Page) {
  // Own company: other journeys may already have an accounting catalog.
  const capability = await page.evaluate(() =>
    window.sessionStorage.getItem('nexora.edit-access.capability'),
  )
  expect(capability).toBeTruthy()
  const created = await page.request.post('/api/master-data/companies', {
    headers: { 'X-Nexora-Edit-Access': capability! },
    data: { name: 'Compañía visual SAP GUI', functionalCurrencyCode: 'HNL' },
  })
  expect(created.ok(), await created.text()).toBeTruthy()
  const company = (await created.json()) as { id: string }
  await page.evaluate((companyId) => {
    window.localStorage.setItem('nexora.activeCompanyId', companyId)
  }, company.id)
}

// Real test records in the isolated E2E database; no intercepted API data.
async function seedRepresentativeData(page: Page) {
  const { companyId, capability } = await page.evaluate(() => ({
    companyId: localStorage.getItem('nexora.activeCompanyId'),
    capability: sessionStorage.getItem('nexora.edit-access.capability'),
  }))
  const post = async (path: string, data: Record<string, unknown>) => {
    const response = await page.request.post(path, {
      headers: { 'X-Nexora-Edit-Access': capability! }, data: { companyId, ...data },
    })
    expect(response.ok(), await response.text()).toBeTruthy()
  }
  await post('/api/projects', { code: 'SAP-QA', name: 'Proyecto de verificación visual', currencyCode: 'HNL' })
  for (const [code, name, accountType] of [
    ['1101', 'Bancos', 'ASSET'], ['1102', 'Inventario de materiales', 'ASSET'],
    ['2101', 'Proveedores', 'LIABILITY'], ['3101', 'Capital', 'EQUITY'],
    ['4101', 'Ingresos de construcción', 'REVENUE'], ['5101', 'Costo de materiales', 'EXPENSE'],
  ]) await post('/api/master-data/accounts', { code, name, accountType, isPostable: true })
  await post('/api/inventory/warehouses', { code: 'QA', name: 'Almacén de verificación' })
  for (const [sku, name] of [['MAT-001', 'Cemento'], ['MAT-002', 'Acero de refuerzo'], ['MAT-003', 'Agregado']]) {
    await post('/api/inventory/items', { sku, name, uom: 'unidad' })
  }
}

async function setTheme(page: Page, themeId: string) {
  // The full visual matrix can outlive the finite Protected Edit capability.
  // Re-verify with the real E2E PIN before each protected preference update.
  const refreshed = await page.evaluate(async (token) => {
    const response = await fetch('/api/edit-access/verify', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
    if (!response.ok) return { ok: false, status: response.status, body: await response.text() }
    const result = (await response.json()) as { capability: string; expiresAt: number }
    sessionStorage.setItem('nexora.edit-access.capability', result.capability)
    sessionStorage.setItem('nexora.edit-access.expires-at', String(result.expiresAt))
    return { ok: true, status: response.status, body: '' }
  }, process.env.E2E_EDIT_ACCESS_TOKEN)
  expect(refreshed.ok, `renovar Protected Edit -> ${refreshed.status}: ${refreshed.body}`).toBeTruthy()
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

async function captureRoute(
  page: Page,
  variant: (typeof VARIANTS)[number],
  viewport: (typeof VIEWPORTS)[number],
  path: string,
  name: string,
) {
  const consoleErrors: string[] = []
  const pageErrors: string[] = []
  const failedRequests: string[] = []
  const onConsole = (message: { type(): string; text(): string }) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  }
  const onPageError = (error: Error) => pageErrors.push(String(error))
  const onResponse = (response: { status(): number; url(): string }) => {
    if (response.status() >= 500) failedRequests.push(`${response.status()} ${response.url()}`)
  }

  page.on('console', onConsole)
  page.on('pageerror', onPageError)
  page.on('response', onResponse)
  try {
    const response = await page.goto(path)
    expect(response?.status(), `${variant} ${viewport.name} ${path}: HTTP`).toBeLessThan(500)
    await expect(page.locator('main')).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('body')).not.toContainText('Application error')
    const overflow = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }))
    expect(
      overflow.scrollWidth,
      `${variant} ${viewport.name} ${path}: sin overflow de documento`,
    ).toBeLessThanOrEqual(overflow.clientWidth + 1)
    await page.waitForLoadState('networkidle')
    if (path === '/proyectos/cockpit') {
      await page.getByLabel('Proyecto', { exact: true }).selectOption({ label: 'SAP-QA · Proyecto de verificación visual' })
      await expect(page.getByText('Presupuesto (BAC)', { exact: true })).toBeVisible()
      await page.waitForLoadState('networkidle')
    }
    if (viewport.width === 1440 && ['contabilidad', 'cockpit', 'inventario'].includes(name)) {
      const accessibility = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze()
      expect(accessibility.violations, JSON.stringify(accessibility.violations.map(({ id, nodes }) => ({ id, targets: nodes.map(({ target }) => target) })))).toEqual([])
    }
    if (viewport.width <= 640) {
      const overlapping = await page.locator('.nx-table--responsive tbody').evaluateAll((bodies) => bodies.some((body) => {
        const rows = Array.from(body.querySelectorAll('tr'))
        return rows.some((row, index) => index > 0 && row.getBoundingClientRect().top < rows[index - 1].getBoundingClientRect().bottom)
      }))
      expect(overlapping, 'stacked mobile records must not overlap').toBe(false)
    }
    await page.screenshot({
      path: `e2e/visual/sap-${variant}-${viewport.name}-${name}.png`,
      fullPage: true,
    })
    expect(consoleErrors, `${variant} ${viewport.name} ${path}: consola limpia`).toEqual([])
    expect(pageErrors, `${variant} ${viewport.name} ${path}: sin pageerror`).toEqual([])
    expect(failedRequests, `${variant} ${viewport.name} ${path}: sin 500`).toEqual([])
  } finally {
    page.off('console', onConsole)
    page.off('pageerror', onPageError)
    page.off('response', onResponse)
  }
}

test('SAP GUI visual acceptance matrix', async ({ page }) => {
  test.setTimeout(60 * 60_000)
  await login(page)
  await unlockProtectedEdit(page)
  await ensureCompany(page)
  await seedRepresentativeData(page)
  await page.reload()

  // Explicit iteration mode; the default acceptance matrix remains complete.
  const representative = process.env.SAP_REPRESENTATIVE === '1'
  const viewports = representative ? VIEWPORTS.filter(({ name }) => ['1440', '768', '390'].includes(name)) : VIEWPORTS
  const routes = representative ? PAGES.filter(({ name }) => ['contabilidad', 'cockpit', 'inventario'].includes(name)) : PAGES

  for (const variant of VARIANTS) {
    await setTheme(page, variant)
    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height })
      for (const { path, name } of routes) {
        await captureRoute(page, variant, viewport, path, name)
      }
    }
  }
})
