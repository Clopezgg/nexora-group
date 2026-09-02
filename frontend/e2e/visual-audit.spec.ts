import { test, expect, type APIRequestContext, type Page } from '@playwright/test'

/**
 * ORDEN MAESTRA §44-§47 — auditoría visual sistemática de TODAS las rutas
 * autenticadas de `routes.tsx` en desktop 1440, tablet 768 y móvil 390.
 *
 * Gates duros (fallan el test):
 *  - scroll horizontal a nivel de documento,
 *  - elementos visibles que se salen del viewport (fuera de un contenedor con
 *    overflow-x deliberado),
 *  - errores de consola / de página / requests fallidas (500) al cargar,
 *  - controles táctiles diminutos en móvil.
 *
 * Reportes (fallan si no están vacíos, con allowlist acotada):
 *  - enums crudos (DRAFT/APPROVED/…) o UUID como texto principal visible.
 *
 * Deja capturas por ruta/viewport en `e2e/visual/`.
 */

const ADMIN_EMAIL = 'admin@nexora.group'
const ADMIN_PASSWORD = 'NexoraAdmin123!'

const VIEWPORTS = [
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'mobile-390', width: 390, height: 844 },
] as const

// routes.tsx real — todas las rutas autenticadas (sin /login, /verificar/:token).
const ROUTES: { path: string; name: string }[] = [
  { path: '/inicio', name: 'home' },
  { path: '/inicio/aprobaciones', name: 'approvals' },
  { path: '/proyectos', name: 'projects' },
  { path: '/proyectos/cockpit', name: 'project-cockpit' },
  { path: '/proyectos/wbs', name: 'wbs' },
  { path: '/proyectos/presupuestos', name: 'budget' },
  { path: '/proyectos/avances', name: 'progress' },
  { path: '/proyectos/ordenes-de-cambio', name: 'change-orders' },
  { path: '/proyectos/diario-de-obra', name: 'daily-log' },
  { path: '/proyectos/rfi-submittals', name: 'rfi-submittals' },
  { path: '/proyectos/calidad', name: 'quality' },
  { path: '/proyectos/seguridad', name: 'safety' },
  { path: '/finanzas/control', name: 'financial-control' },
  { path: '/finanzas/contabilidad', name: 'accounting' },
  { path: '/finanzas/conciliacion-subledger', name: 'subledger-recon' },
  { path: '/finanzas/cierre', name: 'closing-center' },
  { path: '/finanzas/excepciones', name: 'exception-center' },
  { path: '/finanzas/inspector', name: 'transaction-inspector' },
  { path: '/finanzas/libro-contractual', name: 'contract-ledger' },
  { path: '/finanzas/flujo-13-semanas', name: 'cash-forecast' },
  { path: '/finanzas/tesoreria', name: 'treasury' },
  { path: '/finanzas/conciliacion', name: 'bank-reconciliation' },
  { path: '/finanzas/cierres-caja', name: 'cash-closings' },
  { path: '/finanzas/restricciones-fondos', name: 'fund-restrictions' },
  { path: '/finanzas/comprobantes', name: 'vouchers' },
  { path: '/finanzas/cuentas-por-pagar', name: 'accounts-payable' },
  { path: '/finanzas/cuentas-por-cobrar', name: 'accounts-receivable' },
  { path: '/finanzas/activos', name: 'assets' },
  { path: '/abastecimiento/solicitudes', name: 'purchase-requests' },
  { path: '/abastecimiento/comparativos', name: 'bid-comparison' },
  { path: '/abastecimiento/ordenes-de-compra', name: 'purchase-orders' },
  { path: '/abastecimiento/recepciones', name: 'goods-receipts' },
  { path: '/abastecimiento/inventario', name: 'inventory' },
  { path: '/abastecimiento/almacenes', name: 'warehouses' },
  { path: '/abastecimiento/proveedores', name: 'suppliers-contractors' },
  { path: '/abastecimiento/contratos', name: 'execution-contracts' },
  { path: '/comercial/leads', name: 'leads' },
  { path: '/comercial/oportunidades', name: 'opportunities' },
  { path: '/comercial/cotizaciones', name: 'sales-quotations' },
  { path: '/comercial/contratos', name: 'sales-contracts' },
  { path: '/comercial/clientes', name: 'customers' },
  { path: '/comercial/facturacion', name: 'ar-billing' },
  { path: '/comercial/cobros', name: 'ar-collections' },
  { path: '/recursos/personal', name: 'workforce' },
  { path: '/recursos/cuadrillas', name: 'crews' },
  { path: '/recursos/equipos', name: 'equipment' },
  { path: '/recursos/mantenimiento', name: 'maintenance' },
  { path: '/recursos/combustible', name: 'fuel' },
  { path: '/recursos/tiempo', name: 'time-entries' },
  { path: '/control/documentos', name: 'document-control' },
  { path: '/control/evidencias', name: 'evidence' },
  { path: '/control/auditoria', name: 'audit' },
  { path: '/control/reportes', name: 'reports' },
  { path: '/control/configuracion', name: 'settings' },
]

// Enums crudos que NUNCA deben ser el texto principal visible (§14/§42).
const RAW_ENUM = /(^|[\s>([])(DRAFT|POSTED|REVERSED|APPROVED|REVIEW|SCHEDULED|PARTIALLY_PAID|UPCOMING|OVERDUE|CANCELLED|TERMINATED|RECONCILED|NOT_STARTED|IN_PROGRESS|BLOCKED_EXTERNAL)([\s.,)\]<]|$)/
const RAW_UUID = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i

async function login(page: Page) {
  await page.goto('/login')
  await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
  await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: 'Iniciar sesión' }).click()
  await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })
}

async function ensureCompany(request: APIRequestContext) {
  const existing = await request.get('/api/master-data/companies')
  if (existing.ok() && ((await existing.json()) as unknown[]).length > 0) return
  const created = await request.post('/api/master-data/companies', {
    data: { name: 'Auditoría Visual S.A.', functionalCurrencyCode: 'HNL' },
  })
  expect(created.ok(), `crear compañía -> ${created.status()}`).toBeTruthy()
}

async function assertNoHorizontalScroll(page: Page, label: string) {
  const o = await page.evaluate(() => {
    const el = document.documentElement
    return { scroll: el.scrollWidth, client: el.clientWidth }
  })
  expect(o.scroll, `${label}: scroll horizontal (${o.scroll} > ${o.client})`).toBeLessThanOrEqual(
    o.client + 1,
  )
}

async function assertNothingOverflowsViewport(page: Page, label: string) {
  const offenders = await page.evaluate(() => {
    const vw = document.documentElement.clientWidth
    const bad: string[] = []
    const isVisuallyHidden = (s: CSSStyleDeclaration, node: HTMLElement): boolean => {
      if (s.clip === 'rect(0px, 0px, 0px, 0px)' || s.clipPath === 'inset(50%)') return true
      if (s.position === 'absolute' && s.overflow === 'hidden' && node.getBoundingClientRect().width <= 1)
        return true
      return false
    }
    const skipAncestor = (el: HTMLElement): boolean => {
      let node: HTMLElement | null = el.parentElement
      while (node && node !== document.body) {
        const s = getComputedStyle(node)
        if ((s.overflowX === 'auto' || s.overflowX === 'scroll') && node.scrollWidth > node.clientWidth + 1)
          return true
        if (isVisuallyHidden(s, node)) return true
        node = node.parentElement
      }
      return false
    }
    for (const el of Array.from(document.querySelectorAll<HTMLElement>('body *'))) {
      const r = el.getBoundingClientRect()
      if (r.width === 0 || r.height === 0) continue
      const style = getComputedStyle(el)
      if (style.position === 'fixed') continue
      if ((style.overflowX === 'auto' || style.overflowX === 'scroll') && el.scrollWidth > el.clientWidth)
        continue
      if ((r.right > vw + 2 || r.left < -2) && !skipAncestor(el)) {
        bad.push(
          `${el.tagName.toLowerCase()}.${el.className || '(sin clase)'} → left=${Math.round(r.left)} right=${Math.round(r.right)} vw=${vw}`,
        )
      }
    }
    return bad.slice(0, 8)
  })
  expect(offenders, `${label}: elementos fuera del viewport\n${offenders.join('\n')}`).toEqual([])
}

async function assertTouchTargets(page: Page, label: string) {
  const small = await page.evaluate(() => {
    const bad: string[] = []
    for (const el of Array.from(
      document.querySelectorAll<HTMLElement>(
        'button, a[href], [role="tab"], input[type="checkbox"], input[type="radio"]',
      ),
    )) {
      const r = el.getBoundingClientRect()
      if (r.width === 0 || r.height === 0) continue
      if (getComputedStyle(el).display === 'none') continue
      if ((el as HTMLButtonElement).disabled || el.getAttribute('aria-disabled') === 'true') continue
      if (r.height < 32 && r.width < 32)
        bad.push(`${el.tagName.toLowerCase()} "${(el.textContent || '').trim().slice(0, 24)}" ${Math.round(r.width)}x${Math.round(r.height)}`)
    }
    return bad.slice(0, 8)
  })
  expect(small, `${label}: controles táctiles < 32px\n${small.join('\n')}`).toEqual([])
}

function auditViewport(vp: (typeof VIEWPORTS)[number]) {
  test(`Auditoría visual §44 — ${vp.name}`, async ({ page }) => {
    test.setTimeout(240_000)
    await login(page)
    await ensureCompany(page.request)
    await page.setViewportSize({ width: vp.width, height: vp.height })

    const consoleErrors: string[] = []
    page.on('console', (m) => {
      if (m.type() === 'error') consoleErrors.push(m.text())
    })
    page.on('pageerror', (e) => consoleErrors.push(`pageerror: ${e.message}`))
    page.on('response', (r) => {
      if (r.status() >= 500) consoleErrors.push(`${r.status()} ${r.url()}`)
    })

    const rawEnumHits: string[] = []

    for (const route of ROUTES) {
      await test.step(`${vp.name} · ${route.name}`, async () => {
        const before = consoleErrors.length
        await page.goto(route.path)
        await page.waitForLoadState('networkidle').catch(() => {})
        await page.waitForTimeout(350)

        const label = `${vp.name} ${route.path}`
        await assertNoHorizontalScroll(page, label)
        await assertNothingOverflowsViewport(page, label)
        if (vp.width <= 400) await assertTouchTargets(page, label)

        // Errores nuevos en esta ruta.
        const newErrors = consoleErrors.slice(before)
        expect(newErrors, `${label}: errores al cargar\n${newErrors.join('\n')}`).toEqual([])

        // Enum crudo / UUID como texto principal (excluye <code>, [data-testid], title técnico).
        const bodyText = await page.evaluate(() => {
          const clone = document.body.cloneNode(true) as HTMLElement
          clone.querySelectorAll('code, pre, script, style, [data-uuid-ok]').forEach((n) => n.remove())
          return clone.innerText
        })
        const m = bodyText.match(RAW_ENUM)
        if (m) rawEnumHits.push(`${route.path}: «${m[2]}»`)
        if (RAW_UUID.test(bodyText)) rawEnumHits.push(`${route.path}: UUID visible`)

        await page.screenshot({ path: `e2e/visual/${route.name}--${vp.name}.png`, fullPage: true })
      })
    }

    expect(rawEnumHits, `${vp.name}: enums crudos / UUID como texto principal\n${rawEnumHits.join('\n')}`).toEqual([])
  })
}

for (const vp of VIEWPORTS) auditViewport(vp)
