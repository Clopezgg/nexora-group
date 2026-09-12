import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

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

async function expectOperationalRoute(page: Page, path: string) {
  // WebKit reports fetches aborted by a navigation as page errors. Finish the
  // current screen's authoritative requests before navigating so the journey
  // tests the application rather than canceling its own in-flight queries.
  await page.waitForLoadState('networkidle')
  const pageErrors: string[] = []
  const onPageError = (error: Error) => pageErrors.push(String(error))
  page.on('pageerror', onPageError)
  try {
    const response = await page.goto(path)
    expect(response?.status(), `${path}: HTTP`).toBeLessThan(500)
    await expect(page.locator('.nx-app-shell')).toBeVisible({ timeout: 15_000 })
    await expect(page.locator('main')).toBeVisible()
    await page.waitForLoadState('networkidle')
    await expect(page.locator('body')).not.toContainText('Application error')
    expect(pageErrors, `${path}: page errors`).toEqual([])
  } finally {
    page.off('pageerror', onPageError)
  }
}

test('cross-browser critical compatibility', async ({ page }) => {
  await login(page)
  const company = await ensureCompany(page)

  await page.evaluate((companyId) => {
    window.localStorage.setItem('nexora.activeCompanyId', companyId)
  }, company.id)
  await page.reload()

  const dashboard = await page.request.get(
    `/api/dashboard/summary?companyId=${encodeURIComponent(company.id)}`,
  )
  expect(dashboard.ok(), await dashboard.text()).toBeTruthy()
  const dashboardBody = (await dashboard.json()) as { currency: string }
  expect(dashboardBody.currency).toBe(company.functionalCurrencyCode)

  for (const route of [
    '/inicio',
    '/proyectos',
    '/finanzas/cuentas-por-pagar',
    '/finanzas/tesoreria',
    '/control/configuracion',
  ]) {
    await expectOperationalRoute(page, route)
  }

  await page.goto('/inicio')
  await page.getByRole('button', { name: 'Edición protegida' }).click()
  const dialog = page.getByRole('dialog', { name: 'Desbloquear edición' })
  await expect(dialog).toBeVisible()
  await dialog.getByLabel('Token de seguridad').fill(process.env.E2E_EDIT_ACCESS_TOKEN!)
  await dialog.getByRole('button', { name: 'Desbloquear', exact: true }).click()
  await expect(dialog).not.toBeVisible()

  await page.getByRole('button', { name: 'Cerrar sesión' }).click()
  await expect(page).toHaveURL(/\/login/, { timeout: 10_000 })
})
