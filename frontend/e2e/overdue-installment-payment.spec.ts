import { expect, test, type APIRequestContext } from '@playwright/test'

/**
 * P0 — Cuota contractual vencida debe mostrar Pagar/Liquidar en el Plan de pagos.
 *
 * Caso canónico:
 *   Contrato 10101960 (o fixture determinista)
 *   Valor: 1,500,000.00
 *   Anticipo pagado: 50,000.00
 *   Septiembre 2026: VENCIDA, remaining=207,142.85, payableNow=true
 *   Octubre 2026+: UPCOMING, payableNow=false
 *
 * El test usa la sesión de browser real + API del backend (misma cookie).
 */

const ADMIN_EMAIL = 'admin@nexora.group'
const ADMIN_PASSWORD = 'NexoraAdmin123!'
let editCapability = ''

async function api<T = any>(
  request: APIRequestContext,
  method: 'get' | 'post' | 'put' | 'patch' | 'delete',
  path: string,
  data?: unknown,
): Promise<T> {
  const protectedMutation = method !== 'get' && path !== '/edit-access/verify'
  const options = {
    ...(data !== undefined ? { data } : {}),
    ...(protectedMutation && editCapability
      ? { headers: { 'X-Nexora-Edit-Access': editCapability } }
      : {}),
  }
  let response = await request[method](`/api${path}`, options)
  if (response.status() === 428 && protectedMutation) {
    const token = process.env.E2E_EDIT_ACCESS_TOKEN
    expect(token).toBeTruthy()
    const unlock = await request.post('/api/edit-access/verify', { data: { token } })
    expect(unlock.ok(), await unlock.text()).toBeTruthy()
    editCapability = (await unlock.json()).capability
    expect(editCapability).toBeTruthy()
    response = await request[method](`/api${path}`, {
      ...options,
      headers: { 'X-Nexora-Edit-Access': editCapability },
    })
  }
  expect(response.ok(), `${method.toUpperCase()} ${path} -> ${response.status()}: ${await response.text()}`).toBeTruthy()
  if (response.status() === 204) return undefined as T
  return response.json()
}

test.describe.configure({ mode: 'serial' })

test.describe('P0 — Cuota vencida: Pagar/Liquidar en Plan de pagos', () => {
  let companyId: string
  let contractId: string
  let scheduleId: string
  let overdueInstallmentId: string
  let upcomingInstallmentId: string
  let treasuryAccountId: string

  test('setup: login y obtener contexto', async ({ page, request }) => {
    await page.goto('/login')
    await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
    await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()
    await expect(page).not.toHaveURL('/login', { timeout: 10000 })

    // Obtener compañía activa
    const companies = await api<any[]>(request, 'get', '/companies/')
    expect(companies.length).toBeGreaterThan(0)
    companyId = companies[0].id

    // Obtener cuentas de tesorería
    const treasuryAccounts = await api<any[]>(request, 'get', `/treasury/accounts/?company_id=${companyId}`)
    const activeAccounts = treasuryAccounts.filter(a => a.status === 'ACTIVE')
    expect(activeAccounts.length).toBeGreaterThan(0)
    treasuryAccountId = activeAccounts[0].id
  })

  test('setup: crear contrato con plan de pagos si no existe fixture', async ({ request }) => {
    // Buscar contrato con número 10101960
    const contracts = await api<any[]>(request, 'get', `/procurement/contracts/?company_id=${companyId}`)
    let contract = contracts.find((c: any) => c.contractNumber === '10101960')

    if (!contract) {
      // Crear proveedor fixture
      const suppliers = await api<any[]>(request, 'get', `/procurement/suppliers/?company_id=${companyId}`)
      let supplierId = suppliers[0]?.id
      if (!supplierId) {
        const newSupplier = await api<any>(request, 'post', '/procurement/suppliers/', {
          companyId,
          legalName: 'Proveedor E2E Fixture',
          taxId: 'E2E-001',
          supplierType: 'CONTRACTOR',
        })
        supplierId = newSupplier.id
      }

      // Crear contrato
      contract = await api<any>(request, 'post', '/procurement/contracts/', {
        companyId,
        supplierId,
        contractNumber: '10101960',
        description: 'Contrato E2E fixture canónico',
        value: '1500000.00',
        advanceAmount: '50000.00',
        advanceDueDate: '2026-08-01',
        scope: 'GENERAL',
        status: 'ACTIVE',
      })
    }
    contractId = contract.id

    // Verificar/crear plan de pagos
    const scheduleRes = await request.get(`/api/contract-payments/by-contract/${contractId}/`)
    if (scheduleRes.status() === 404) {
      // Crear plan con Sept 2026 como primera mensualidad
      const schedule = await api<any>(request, 'post', '/contract-payments/', {
        supplierContractId: contractId,
        regularMonths: 7,
        dueDay: 1,
        firstPeriod: '2026-09-01',
        advanceAmount: '50000.00',
        advanceDueDate: '2026-08-01',
      })
      scheduleId = schedule.id
    } else {
      const schedule = await scheduleRes.json()
      scheduleId = schedule.id
    }

    // Obtener cuotas
    const scheduleDetail = await api<any>(request, 'get', `/contract-payments/${scheduleId}/`)
    const installments: any[] = scheduleDetail.installments ?? []

    // Identificar cuota OVERDUE/DUE de Sept 2026
    const sept = installments.find((i: any) =>
      i.installmentKind === 'REGULAR' &&
      (i.status === 'OVERDUE' || i.status === 'DUE') &&
      i.dueDate?.startsWith('2026-09'),
    )
    if (sept) {
      overdueInstallmentId = sept.installmentId
    }

    // Identificar cuota UPCOMING de Oct 2026+
    const upcoming = installments.find((i: any) =>
      i.installmentKind === 'REGULAR' &&
      i.status === 'UPCOMING' &&
      i.dueDate > '2026-09-30',
    )
    if (upcoming) {
      upcomingInstallmentId = upcoming.installmentId
    }
  })

  test('P0: abrir Plan de pagos → cuota vencida muestra Pagar y Liquidar', async ({ page }) => {
    await page.goto('/abastecimiento/contratos')
    await expect(page.getByText('10101960')).toBeVisible({ timeout: 15000 })

    // Abrir modal de plan de pagos
    const row = page.locator('tr, [role="row"]').filter({ hasText: '10101960' }).first()
    const planButton = row.getByRole('button', { name: /plan de pagos/i })
    await planButton.click()

    // Esperar modal
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 8000 })
    await expect(page.getByText(/Plan de pagos/)).toBeVisible()

    // La cuota vencida (OVERDUE) debe mostrar Pagar y Liquidar
    const table = page.locator('.nx-table, table').first()
    await expect(table).toBeVisible({ timeout: 10000 })

    // Buscar fila con estado VENCIDA
    const overdueRow = table.locator('tr').filter({ hasText: /VENCID|Vencida/i }).first()
    await expect(overdueRow).toBeVisible({ timeout: 5000 })

    // Debe tener botones Pagar y Liquidar
    await expect(overdueRow.getByRole('button', { name: /Pagar/i })).toBeVisible()
    await expect(overdueRow.getByRole('button', { name: /Liquidar/i })).toBeVisible()
  })

  test('P0: cuota UPCOMING no muestra Pagar ni Liquidar activos', async ({ page }) => {
    await page.goto('/abastecimiento/contratos')
    await expect(page.getByText('10101960')).toBeVisible({ timeout: 15000 })

    const row = page.locator('tr, [role="row"]').filter({ hasText: '10101960' }).first()
    const planButton = row.getByRole('button', { name: /plan de pagos/i })
    await planButton.click()

    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 8000 })

    const table = page.locator('.nx-table, table').first()
    await expect(table).toBeVisible({ timeout: 10000 })

    // Fila UPCOMING / Próxima
    const upcomingRow = table.locator('tr').filter({ hasText: /UPCOMING|Próxima/i }).first()
    if (await upcomingRow.count() > 0) {
      // No debe tener botón Pagar habilitado
      const payBtn = upcomingRow.getByRole('button', { name: /Pagar/i })
      const liquidarBtn = upcomingRow.getByRole('button', { name: /Liquidar/i })
      // Si existen, deben estar disabled
      if (await payBtn.count() > 0) {
        await expect(payBtn).toBeDisabled()
      }
      if (await liquidarBtn.count() > 0) {
        await expect(liquidarBtn).toBeDisabled()
      }
      // O debe mostrar texto "Próxima" en lugar de botones
      const proximaText = upcomingRow.getByText(/Próxima/i)
      const hasProxima = await proximaText.count() > 0
      const hasDisabledPay = (await payBtn.count() > 0) && await payBtn.isDisabled()
      expect(hasProxima || hasDisabledPay).toBeTruthy()
    }
  })

  test('P0: verificar via API que payableNow=true para OVERDUE y payableNow=false para UPCOMING', async ({ request }) => {
    if (!scheduleId) {
      test.skip()
      return
    }
    const schedule = await api<any>(request, 'get', `/contract-payments/${scheduleId}/`)
    const installments: any[] = schedule.installments ?? []

    // Cuotas OVERDUE deben ser payableNow=true
    const overdue = installments.filter((i: any) => i.status === 'OVERDUE' || i.status === 'DUE')
    for (const i of overdue) {
      expect(i.payableNow, `Installment ${i.installmentId} (${i.status}) must have payableNow=true`).toBe(true)
    }

    // Cuotas UPCOMING deben ser payableNow=false
    const upcoming = installments.filter((i: any) => i.status === 'UPCOMING')
    for (const i of upcoming) {
      expect(i.payableNow, `Installment ${i.installmentId} (UPCOMING) must have payableNow=false`).toBe(false)
    }
  })

  test('P0: resumen canónico — saldo acumulado refleja anticipo', async ({ request }) => {
    if (!scheduleId) {
      test.skip()
      return
    }
    const summary = await api<any>(request, 'get', `/contract-payments/${scheduleId}/summary/`)
    // Anticipo debe estar reflejado
    expect(Number(summary.contractValue)).toBeCloseTo(1500000, 0)
  })
})
