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
  // La matriz completa puede superar el TTL de Protected Edit. Renueva la
  // capability con el PIN real antes de cada preferencia protegida, evitando
  // que una corrida larga falle por expiración temporal.
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
  await setTheme(page, 'nexora-horizon-light')
  await page.goto('/control/configuracion')
  await page.waitForLoadState('networkidle')

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

  await expect(page.getByLabel('Variante')).toHaveValue('sap-gui-signature')
  await page.getByLabel('Variante').selectOption('sap-gui-tradeshow')
  await expect(page.getByRole('dialog', { name: 'Cambiar a SAP GUI' })).toHaveCount(0)
  await page.getByRole('button', { name: 'Guardar como mi preferencia' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-nx-sap-variant', 'tradeshow')

  // Las variantes modernas cambian de anatomía sin reconfirmar.
  await page.getByLabel('Variante').selectOption('sap-gui-horizon')
  await expect(page.getByRole('dialog', { name: 'Cambiar a SAP GUI' })).toHaveCount(0)
  await expect(page.locator('html')).toHaveAttribute('data-nx-anatomy', 'sap-gui-horizon')
  await expect(page.locator('html')).toHaveAttribute('data-nx-toolbar', 'horizon')
  await page.getByRole('button', { name: 'Guardar como mi preferencia' }).click()

  await page.getByLabel('Variante').selectOption('sap-gui-horizon-dark')
  await expect(page.locator('html')).toHaveAttribute('data-nx-anatomy', 'sap-gui-horizon-dark')
  await expect(page.locator('html')).toHaveAttribute('data-nx-toolbar', 'horizon-dark')
  await page.getByRole('button', { name: 'Guardar como mi preferencia' }).click()

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
  const navButton = page.locator('.nx-sap-toolbar button[aria-label="Abrir navegación"]')
  await expect(navButton).toBeVisible()
  await navButton.click()
  await expect(page.getByRole('dialog', { name: 'Navegación' })).toBeVisible()
  const viewport = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(viewport.scrollWidth).toBeLessThanOrEqual(viewport.clientWidth + 1)
})

const SAP_VARIANTS = [
  { id: 'sap-gui-signature', variant: 'signature', anatomy: 'sap-gui-signature' },
  { id: 'sap-gui-tradeshow', variant: 'tradeshow', anatomy: 'sap-gui-tradeshow' },
  { id: 'sap-gui-horizon', variant: 'horizon', anatomy: 'sap-gui-horizon' },
  { id: 'sap-gui-horizon-dark', variant: 'horizon-dark', anatomy: 'sap-gui-horizon-dark' },
] as const

const REPRESENTATIVE_ROUTES = [
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

// Inventario completo de rutas reales (navigation.ts) para la auditoría SAP.
const FULL_ROUTE_INVENTORY = [
  ...REPRESENTATIVE_ROUTES,
  '/inicio/aprobaciones',
  '/finanzas/contabilidad',
  '/finanzas/conciliacion-subledger',
  '/finanzas/cierre',
  '/finanzas/excepciones',
  '/finanzas/inspector',
  '/finanzas/libro-contractual',
  '/finanzas/flujo-13-semanas',
  '/finanzas/conciliacion',
  '/finanzas/cierres-caja',
  '/finanzas/restricciones-fondos',
  '/finanzas/comprobantes',
  '/finanzas/cuentas-por-cobrar',
  '/finanzas/activos',
  '/proyectos/wbs',
  '/proyectos/presupuestos',
  '/proyectos/cockpit',
  '/proyectos/avances',
  '/proyectos/ordenes-de-cambio',
  '/proyectos/diario-de-obra',
  '/proyectos/calidad',
  '/proyectos/seguridad',
  '/proyectos/rfi-submittals',
  '/abastecimiento/comparativos',
  '/abastecimiento/ordenes-de-compra',
  '/abastecimiento/recepciones',
  '/abastecimiento/inventario',
  '/abastecimiento/almacenes',
  '/abastecimiento/proveedores',
  '/abastecimiento/contratos',
  '/comercial/leads',
  '/comercial/oportunidades',
  '/comercial/clientes',
  '/comercial/cotizaciones',
  '/comercial/contratos',
  '/comercial/facturacion',
  '/comercial/cobros',
  '/recursos/cuadrillas',
  '/recursos/tiempo',
  '/recursos/combustible',
  '/recursos/mantenimiento',
  '/control/evidencias',
  '/control/auditoria',
]

test('all four SAP GUI variants render representative routes with real chrome', async ({ page }) => {
  await login(page)
  await unlockProtectedEdit(page)
  await ensureCompany(page.request)

  for (const { id, variant, anatomy } of SAP_VARIANTS) {
    await setTheme(page, id)
    await expect(page.locator('html')).toHaveAttribute('data-nx-family', 'sap-gui')
    await expect(page.locator('html')).toHaveAttribute('data-nx-sap-variant', variant)
    await expect(page.locator('html')).toHaveAttribute('data-nx-anatomy', anatomy)

    for (const route of REPRESENTATIVE_ROUTES) {
      await page.goto(route)
      await expect(page.locator('html')).toHaveAttribute('data-nx-theme', id)
      await expect(page.locator('main')).toBeVisible()
      await expect(page.getByRole('menubar', { name: 'Barra de menús SAP GUI' })).toBeVisible()
      await expect(page.getByRole('toolbar', { name: 'Barra de herramientas SAP GUI' })).toBeVisible()
      await expect(page.getByRole('status', { name: 'Contexto SAP GUI' })).toBeVisible()
      await expect(page.locator('body')).not.toContainText('Application error')
      const viewport = await page.evaluate(() => ({
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
      }))
      expect(viewport.scrollWidth, `${id} ${route}: sin overflow horizontal`).toBeLessThanOrEqual(viewport.clientWidth + 1)
    }

    // Axe por variante en una ruta financiera densa.
    await page.goto('/finanzas/cuentas-por-pagar')
    await expect(page.locator('html')).toHaveAttribute('data-nx-theme', id)
    await page.waitForLoadState('networkidle')
    const accessibility = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze()
    expect(accessibility.violations, `${id}: ${formatViolations(accessibility)}`).toEqual([])
  }
})

test('SAP GUI full route inventory: no crash, no overflow, chrome intact', async ({ page }) => {
  await login(page)
  await unlockProtectedEdit(page)
  await ensureCompany(page.request)
  await setTheme(page, 'sap-gui-signature')

  for (const route of FULL_ROUTE_INVENTORY) {
    await page.goto(route)
    await expect(page.locator('main'), `${route}: main visible`).toBeVisible()
    await expect(page.locator('body'), `${route}: sin error de aplicación`).not.toContainText('Application error')
    await expect(
      page.getByRole('menubar', { name: 'Barra de menús SAP GUI' }),
      `${route}: menubar SAP`,
    ).toBeVisible()
    await expect(
      page.getByRole('status', { name: 'Contexto SAP GUI' }),
      `${route}: status bar SAP`,
    ).toBeVisible()
    const viewport = await page.evaluate(() => ({
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
    }))
    expect(viewport.scrollWidth, `${route}: sin overflow horizontal`).toBeLessThanOrEqual(viewport.clientWidth + 1)
  }
})

test('SAP GUI theme persists across reload and exits cleanly to Quartz', async ({ page }) => {
  await login(page)
  await unlockProtectedEdit(page)
  await ensureCompany(page.request)
  await setTheme(page, 'sap-gui-horizon-dark')
  await page.reload()
  await expect(page.locator('html')).toHaveAttribute('data-nx-theme', 'sap-gui-horizon-dark')
  await expect(page.locator('html')).toHaveAttribute('data-nx-family', 'sap-gui')

  await setTheme(page, 'quartz-light')
  await expect(page.getByRole('menubar', { name: 'Barra de menús SAP GUI' })).toHaveCount(0)
  await expect(page.getByRole('status', { name: 'Contexto SAP GUI' })).toHaveCount(0)
  await expect(page.locator('html')).not.toHaveAttribute('data-nx-sap-variant', 'horizon-dark')
})

test('a modern family never mounts SAP GUI chrome', async ({ page }) => {
  await login(page)
  await unlockProtectedEdit(page)
  await ensureCompany(page.request)
  await setTheme(page, 'quartz-light')
  await expect(page.getByRole('menubar', { name: 'Barra de menús SAP GUI' })).toHaveCount(0)
  await expect(page.getByRole('status', { name: 'Contexto SAP GUI' })).toHaveCount(0)
})


test('SAP menus and command results remain clickable outside compact bars', async ({ page }) => {
  await login(page)
  await unlockProtectedEdit(page)
  await ensureCompany(page.request)
  for (const theme of SAP_VARIANTS) {
    await setTheme(page, theme.id)
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 })
      await page.getByRole('menuitem', { name: 'Sistema', exact: true }).click()
      await page.getByRole('menu', { name: 'Sistema', exact: true }).getByRole('menuitem', { name: 'Inicio', exact: true }).click()
      await expect(page).toHaveURL(/\/inicio/)
      const command = page.getByRole('combobox', { name: 'Comando: buscar módulo, documento o acción' })
      await command.fill('Inventario')
      await page.getByRole('listbox', { name: 'Resultados del comando' }).getByRole('button', { name: /Inventario/ }).click()
      await expect(page).toHaveURL(/\/abastecimiento\/inventario/)
    }
  }
})

test('SAP menubar keyboard traverses bar and open menus with focus restoration', async ({ page }) => {
  await login(page)
  await unlockProtectedEdit(page)
  await setTheme(page, 'sap-gui-signature')
  const sistema = page.getByRole('menuitem', { name: 'Sistema', exact: true })
  const ayuda = page.getByRole('menuitem', { name: 'Ayuda', exact: true })
  await sistema.focus()
  await page.keyboard.press('End')
  await expect(ayuda).toBeFocused()
  await page.keyboard.press('Home')
  await expect(sistema).toBeFocused()
  await page.keyboard.press('ArrowUp')
  const sistemaMenu = page.getByRole('menu', { name: 'Sistema', exact: true })
  await expect(sistemaMenu.getByRole('menuitem').last()).toBeFocused()
  await page.keyboard.press('Home')
  await expect(sistemaMenu.getByRole('menuitem').first()).toBeFocused()
  await page.keyboard.press('ArrowRight')
  const editarMenu = page.getByRole('menu', { name: 'Editar', exact: true })
  await expect(editarMenu.getByRole('menuitem').first()).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('menuitem', { name: 'Editar', exact: true })).toBeFocused()
  await expect(editarMenu).not.toBeVisible()
})

const SAP_DNA = [
  ['signature', 'folder', 'titled-box', 'classic-blue', 'beveled', 'grid', 'window', 'signature'],
  ['tradeshow', 'raised-folder', 'banded-box', 'tradeshow-blue', 'gradient', 'banded-grid', 'window-banded', 'tradeshow'],
  ['horizon', 'modern-folder', 'modern-titled-box', 'horizon-compact', 'horizon-tool', 'enterprise-grid', 'horizon-window', 'horizon'],
  ['horizon-dark', 'modern-folder', 'dark-titled-box', 'horizon-dark-compact', 'horizon-dark-tool', 'enterprise-grid-dark', 'horizon-window-dark', 'horizon-dark'],
] as const

test('SAP visual DNA resolves component anatomy and non-palette structural differences', async ({ page }, testInfo) => {
  test.setTimeout(120_000)
  await login(page)
  await unlockProtectedEdit(page)
  await ensureCompany(page.request)
  await page.setViewportSize({ width: 1440, height: 900 })
  const fingerprints: Record<string, unknown> = {}
  for (const [variant, ...modes] of SAP_DNA) {
    await setTheme(page, `sap-gui-${variant}`)
    await page.goto('/control/configuracion')
    await expect(page.locator('html')).toHaveAttribute('data-nx-sap-variant', variant)
    for (const [index, attribute] of ['tabs', 'panel', 'field', 'button', 'table', 'dialog', 'toolbar'].entries()) {
      await expect(page.locator('html')).toHaveAttribute(`data-nx-${attribute}`, modes[index])
    }
    const measured = await page.evaluate(() => {
      const selectors = ['.nx-sap-titlebar', '.nx-sap-toolbar', '.nx-card', '.nx-select', '.nx-button']
      return selectors.map((selector) => {
        const element = document.querySelector(selector)
        if (!element) throw new Error(`Missing real component: ${selector}`)
        const style = getComputedStyle(element)
        return {
          selector,
          radius: style.borderRadius,
          borderWidth: style.borderWidth,
          borderStyle: style.borderStyle,
          padding: style.padding,
          height: style.height,
          fontSize: style.fontSize,
          fontWeight: style.fontWeight,
          shadow: style.boxShadow.replace(/rgba?\([^)]+\)/g, 'COLOR'),
          gradient: style.backgroundImage.replace(/rgba?\([^)]+\)/g, 'COLOR'),
        }
      })
    })
    const title = measured.find(({ selector }) => selector === '.nx-sap-titlebar')!
    const field = measured.find(({ selector }) => selector === '.nx-select')!
    const modern = variant.startsWith('horizon')
    expect(parseFloat(title.height), `${variant}: measured titlebar`).toBe(modern ? 28 : 26)
    expect(parseFloat(field.height), `${variant}: compact field`).toBe(modern ? 30 : 28)
    await page.goto('/abastecimiento/inventario')
    await page.waitForLoadState('networkidle')
    await expect(page.getByRole('tab').first()).toBeVisible()
    await page.getByRole('button', { name: 'Edición habilitada', exact: true }).click()
    const protectedButton = page.getByRole('button', { name: 'Edición protegida', exact: true })
    await protectedButton.click()
    const dialog = page.getByRole('dialog', { name: 'Desbloquear edición' })
    await expect(dialog).toBeVisible()
    const componentStyles = await page.evaluate(() => ['.nx-tabs__tab', '.nx-tabs__panel', '.nx-modal', '.nx-modal__header'].map((selector) => {
      const element = document.querySelector(selector)
      if (!element) throw new Error(`Missing component: ${selector}`)
      const style = getComputedStyle(element)
      return { selector, height: style.height, padding: style.padding, borderWidth: style.borderWidth, radius: style.borderRadius, shadow: style.boxShadow.replace(/rgba?\([^)]+\)/g, 'COLOR'), gradient: style.backgroundImage.replace(/rgba?\([^)]+\)/g, 'COLOR') }
    }))
    await page.keyboard.press('Escape')
    await expect(dialog).not.toBeVisible()
    await expect(protectedButton).toBeFocused()
    await page.setViewportSize({ width: 390, height: 844 })
    await expect(page.getByRole('combobox', { name: 'Comando: buscar módulo, documento o acción' })).toBeVisible()
    const touchHeights = await page.locator('.nx-sap-commandbar button').evaluateAll((buttons) => buttons.filter((button) => button.getBoundingClientRect().width > 0).map((button) => button.getBoundingClientRect().height))
    expect(touchHeights.every((height) => height >= 40), `${variant}: command touch targets`).toBe(true)
    await page.setViewportSize({ width: 1440, height: 900 })
    fingerprints[variant] = { measured, componentStyles }
  }
  await testInfo.attach('SAP non-color geometry fingerprints', { body: JSON.stringify(fingerprints, null, 2), contentType: 'application/json' })
  // The classic variants must differ in actual CSS geometry/depth, even with
  // every color stripped. Modern dark keeps the Horizon geometry by design.
  expect(fingerprints.signature).not.toEqual(fingerprints.tradeshow)
  expect(fingerprints.signature).not.toEqual(fingerprints.horizon)
  expect(fingerprints.tradeshow).not.toEqual(fingerprints.horizon)
})

test('SAP tree supports expansion, hierarchy, boundaries and typeahead', async ({ page }) => {
  await login(page)
  await unlockProtectedEdit(page)
  await setTheme(page, 'sap-gui-signature')
  const tree = page.getByRole('tree', { name: 'Navegación principal', exact: true })
  const first = tree.getByRole('treeitem').first()
  await first.focus()
  await page.keyboard.press('ArrowLeft')
  await expect(first).toHaveAttribute('aria-expanded', 'false')
  await page.keyboard.press('ArrowRight')
  await expect(first).toHaveAttribute('aria-expanded', 'true')
  await page.keyboard.press('ArrowRight')
  await expect(tree.locator('[data-kind="link"]').first()).toBeFocused()
  await page.keyboard.press('ArrowLeft')
  await expect(first).toBeFocused()
  await page.keyboard.press('End')
  await expect(tree.getByRole('treeitem').last()).toBeFocused()
  await page.keyboard.press('Home')
  await expect(first).toBeFocused()
  await page.keyboard.press('f')
  await expect(tree.locator('[data-kind="group"]', { hasText: 'Finanzas' })).toBeFocused()
})
