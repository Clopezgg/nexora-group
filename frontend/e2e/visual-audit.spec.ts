import { test, expect, type APIRequestContext, type Page } from '@playwright/test'
import { navItems } from '../src/app/navigation'

/**
 * ORDEN MAESTRA §44-§47 — auditoría visual sistemática de TODAS las rutas
 * autenticadas de `routes.tsx` en los nueve anchos de aceptación: 360, 390,
 * 430, 768, 1024, 1280, 1366, 1440 y 1920 px.
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
  { name: 'desktop-1920', width: 1920, height: 1080 },
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'desktop-1366', width: 1366, height: 900 },
  { name: 'desktop-1280', width: 1280, height: 900 },
  { name: 'laptop-1024', width: 1024, height: 900 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'mobile-430', width: 430, height: 932 },
  { name: 'mobile-390', width: 390, height: 844 },
  { name: 'mobile-360', width: 360, height: 800 },
] as const

// routes.tsx real — todas las rutas autenticadas (sin /login, /verificar/:token).
// The audited inventory derives from production navigation, so adding a
// navigable route automatically adds it to the visual matrix.
const ROUTES: { path: string; name: string }[] = navItems.map((item) => ({
  path: item.path,
  name: item.path.slice(1).replaceAll('/', '-'),
}))

// Enums crudos que NUNCA deben ser el texto principal visible (§14/§42).
const RAW_ENUM = /(^|[\s>([])(DRAFT|POSTED|REVERSED|APPROVED|REVIEW|SCHEDULED|PARTIALLY_PAID|UPCOMING|OVERDUE|CANCELLED|TERMINATED|RECONCILED|NOT_STARTED|IN_PROGRESS|BLOCKED_EXTERNAL)([\s.,)\]<]|$)/
const RAW_UUID = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/i

async function login(page: Page) {
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    await page.goto('/login')
    await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
    await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()
    try {
      await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })
      return
    } catch (error) {
      if (attempt === 3) throw error
      await page.waitForTimeout(3_000)
    }
  }
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
        await page.waitForLoadState('networkidle', { timeout: 15_000 })
        await page.waitForTimeout(350)

        const label = `${vp.name} ${route.path}`
        await assertNoHorizontalScroll(page, label)
        await assertNothingOverflowsViewport(page, label)
        const sapIconLeaks = await page.locator('.nx-sap-tree__link-icon:visible').evaluateAll((icons) =>
          icons.flatMap((icon) => {
            const text = (icon.textContent ?? '').trim()
            return icon.querySelector('svg.nx-icon') && !text ? [] : [text || 'missing SVG']
          }),
        )
        expect(sapIconLeaks, `${label}: SAP icons must not leak IconName text`).toEqual([])
        if (vp.width <= 430) await assertTouchTargets(page, label)

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
