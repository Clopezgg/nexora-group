import { test, expect, type APIRequestContext, type Page } from '@playwright/test'

/**
 * ORDEN MAESTRA §50 — auditoría visual sistemática.
 *
 * Recorre las pantallas autenticadas clave en desktop 1440, tablet 768 y
 * móvil 390 y **falla** ante los defectos que §50 enumera: scroll horizontal,
 * elementos que se salen del viewport, controles táctiles diminutos en móvil,
 * y la presencia de "S1..S13" como lenguaje principal en el Home. Además deja
 * capturas en `e2e/visual/` para inspección.
 *
 * No es solo archivar screenshots: cada aserción es un gate.
 */

const ADMIN_EMAIL = 'admin@nexora.group'
const ADMIN_PASSWORD = 'NexoraAdmin123!'

const VIEWPORTS = [
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'mobile-390', width: 390, height: 844 },
] as const

const ROUTES = [
  { path: '/inicio', name: 'home' },
  { path: '/finanzas/flujo-13-semanas', name: 'cash-flow' },
  { path: '/proyectos', name: 'projects' },
  { path: '/abastecimiento/contratos', name: 'contracts' },
  { path: '/finanzas/cuentas-por-pagar', name: 'accounts-payable' },
  { path: '/finanzas/comprobantes', name: 'vouchers' },
  { path: '/control/auditoria', name: 'audit' },
  { path: '/control/configuracion', name: 'settings' },
] as const

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

/** Detecta scroll horizontal a nivel de documento (tolerancia 1px). */
async function assertNoHorizontalScroll(page: Page, label: string) {
  const overflow = await page.evaluate(() => {
    const el = document.documentElement
    return { scroll: el.scrollWidth, client: el.clientWidth }
  })
  expect(
    overflow.scroll,
    `${label}: scroll horizontal (${overflow.scroll} > ${overflow.client})`,
  ).toBeLessThanOrEqual(overflow.client + 1)
}

/**
 * Ningún elemento visible debe sobresalir del ancho del viewport, salvo que
 * viva dentro de un contenedor con scroll horizontal deliberado (§38 permite
 * tablas anchas scrolleables). El gate duro de scroll de página es
 * `assertNoHorizontalScroll`; este detecta cards/inputs/textos que se salen.
 */
async function assertNothingOverflowsViewport(page: Page, label: string) {
  const offenders = await page.evaluate(() => {
    const vw = document.documentElement.clientWidth
    const bad: string[] = []
    const isVisuallyHidden = (s: CSSStyleDeclaration, node: HTMLElement): boolean => {
      // Patrón sr-only / clip: pintado oculto aunque el bounding box no se
      // encoja (p. ej. el <thead> de una tabla responsive apilada).
      if (s.clip === 'rect(0px, 0px, 0px, 0px)' || s.clipPath === 'inset(50%)') return true
      if (
        s.position === 'absolute' &&
        s.overflow === 'hidden' &&
        node.getBoundingClientRect().width <= 1
      ) {
        return true
      }
      return false
    }
    const skipAncestor = (el: HTMLElement): boolean => {
      let node: HTMLElement | null = el.parentElement
      while (node && node !== document.body) {
        const s = getComputedStyle(node)
        if (
          (s.overflowX === 'auto' || s.overflowX === 'scroll') &&
          node.scrollWidth > node.clientWidth + 1
        ) {
          return true
        }
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
      if (
        (style.overflowX === 'auto' || style.overflowX === 'scroll') &&
        el.scrollWidth > el.clientWidth
      ) {
        continue
      }
      if ((r.right > vw + 2 || r.left < -2) && !skipAncestor(el)) {
        bad.push(
          `${el.tagName.toLowerCase()}.${el.className || '(sin clase)'} → left=${Math.round(
            r.left,
          )} right=${Math.round(r.right)} vw=${vw}`,
        )
      }
    }
    return bad.slice(0, 8)
  })
  expect(offenders, `${label}: elementos fuera del viewport\n${offenders.join('\n')}`).toEqual([])
}

/** En móvil, los controles interactivos deben tener un objetivo táctil >= 32px. */
async function assertTouchTargets(page: Page, label: string) {
  const small = await page.evaluate(() => {
    const bad: string[] = []
    const controls = Array.from(
      document.querySelectorAll<HTMLElement>(
        'button, a[href], [role="tab"], input[type="checkbox"], input[type="radio"]',
      ),
    )
    for (const el of controls) {
      const r = el.getBoundingClientRect()
      if (r.width === 0 || r.height === 0) continue
      if (getComputedStyle(el).display === 'none') continue
      // Un control deshabilitado no es un objetivo táctil.
      if ((el as HTMLButtonElement).disabled || el.getAttribute('aria-disabled') === 'true') continue
      if (r.height < 32 && r.width < 32) {
        bad.push(`${el.tagName.toLowerCase()} "${(el.textContent || '').trim().slice(0, 24)}" ${Math.round(r.width)}x${Math.round(r.height)}`)
      }
    }
    return bad.slice(0, 8)
  })
  expect(small, `${label}: controles táctiles < 32px\n${small.join('\n')}`).toEqual([])
}

test('Auditoría visual §50 — 1440 / 768 / 390', async ({ page }) => {
  await login(page)
  await ensureCompany(page.request)

  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.width, height: vp.height })

    for (const route of ROUTES) {
      await test.step(`${vp.name} · ${route.name}`, async () => {
        await page.goto(route.path)
        // Deja que carguen datos/gráficas.
        await page.waitForLoadState('networkidle').catch(() => {})
        await page.waitForTimeout(400)

        const label = `${vp.name} ${route.path}`
        await assertNoHorizontalScroll(page, label)
        await assertNothingOverflowsViewport(page, label)
        if (vp.width <= 400) await assertTouchTargets(page, label)

        if (route.name === 'home' || route.name === 'cash-flow') {
          const body = (await page.locator('body').innerText()).replace(/\s+/g, ' ')
          expect(body, `${label}: "S1..S13" como etiqueta principal`).not.toMatch(
            /(^|\s)S(1[0-3]|[1-9])(\s|$)/,
          )
        }

        await page.screenshot({
          path: `e2e/visual/${route.name}--${vp.name}.png`,
          fullPage: true,
        })
      })
    }

    // Componentes nuevos que no aparecen sin datos: el asistente de proyecto.
    await test.step(`${vp.name} · project-wizard`, async () => {
      await page.goto('/proyectos')
      await page.getByRole('button', { name: 'Nuevo proyecto' }).click()
      await expect(page.getByLabel('Nombre del proyecto')).toBeVisible()
      const label = `${vp.name} project-wizard`
      await assertNoHorizontalScroll(page, label)
      await assertNothingOverflowsViewport(page, label)
      await page.screenshot({ path: `e2e/visual/project-wizard--${vp.name}.png`, fullPage: true })
      await page.getByRole('button', { name: 'Cerrar asistente' }).click()
    })
  }
})
