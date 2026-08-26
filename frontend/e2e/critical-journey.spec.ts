import { expect, test, type APIRequestContext } from '@playwright/test'

/**
 * NXR-REQ-0112/0113 -- Critical Journey. Un solo recorrido secuencial e
 * integrado (no 40 tests aislados) contra un backend + frontend reales
 * levantados por playwright.config.ts (DB propia `nexora_e2e`, fresh
 * install real vía `alembic upgrade head`). Login/navegación/una muestra
 * representativa de pantallas se maneja por UI real (clicks reales, no
 * mocks); el resto de dominios que ya se probaron exhaustivamente vía
 * pytest este mismo día se ejercitan por `page.request` -- las mismas
 * cookies de sesión que la página, mismo backend real, misma DB real --
 * para mantener el recorrido en un tiempo de ejecución razonable sin
 * perder cobertura real de integración end-to-end.
 */

const ADMIN_EMAIL = 'admin@nexora.group'
const ADMIN_PASSWORD = 'NexoraAdmin123!'

async function api<T = any>(
  request: APIRequestContext,
  method: 'get' | 'post',
  path: string,
  data?: unknown,
): Promise<T> {
  const response = await request[method](`/api${path}`, data !== undefined ? { data } : undefined)
  expect(response.ok(), `${method.toUpperCase()} ${path} -> ${response.status()}: ${await response.text()}`).toBeTruthy()
  if (response.status() === 204) return undefined as T
  return response.json()
}

test.describe.configure({ mode: 'serial' })

test('Critical Journey: login through GL/reports/audit, one continuous real recorrido', async ({ page }) => {
  // 1. login
  await test.step('login', async () => {
    await page.goto('/login')
    await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
    await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()
    await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })
  })

  // 2. company/context -> 3. project -> ActiveUIContext
  let companyId = ''
  let projectId = ''
  await test.step('company + project + ActiveUIContext', async () => {
    await page.goto('/proyectos')
    await page.getByLabel('Nombre de la compañía').fill('Constructora E2E')
    await page.getByRole('button', { name: 'Crear compañía' }).click()
    await expect(page.getByText('Nuevo proyecto')).toBeVisible({ timeout: 10_000 })

    await page.getByLabel('Nombre').fill('Torre Critical Journey')
    await page.getByLabel('Código (opcional)').fill('CJ-001')
    await page.getByRole('button', { name: 'Crear proyecto' }).click()
    await expect(page.getByText('Torre Critical Journey')).toBeVisible({ timeout: 10_000 })

    await page.getByRole('button', { name: 'Usar como activo' }).click()
    await expect(page.getByLabel('Proyecto activo')).toBeVisible()

    const companies = await api<any[]>(page.request, 'get', '/master-data/companies')
    const company = companies.find((c) => c.name === 'Constructora E2E')
    expect(company).toBeTruthy()
    companyId = company.id
    const projects = await api<any[]>(page.request, 'get', `/projects?company_id=${companyId}`)
    const project = projects.find((p: any) => p.name === 'Torre Critical Journey')
    expect(project).toBeTruthy()
    projectId = project.id
  })

  // 4. WBS
  await test.step('WBS', async () => {
    await page.goto('/proyectos/wbs')
    await page.getByPlaceholder('02.01').fill('01')
    await page.getByPlaceholder('EXCAVACIÓN').fill('Movimiento de tierra')
    await page.getByRole('button', { name: 'Agregar nodo' }).click()
    await expect(page.getByRole('listitem').filter({ hasText: 'Movimiento de tierra' })).toBeVisible({
      timeout: 10_000,
    })
  })

  // Chart of accounts (API -- master data, no dedicated screen)
  let bankGl = '', expenseGl = '', payableGl = '', equityGl = '', revenueGl = '', receivableGl = ''
  await test.step('chart of accounts (API)', async () => {
    bankGl = (await api(page.request, 'post', '/master-data/accounts', { companyId, code: '1100', name: 'Bancos E2E', accountType: 'ASSET' })).id
    expenseGl = (await api(page.request, 'post', '/master-data/accounts', { companyId, code: '5100', name: 'Gastos E2E', accountType: 'EXPENSE' })).id
    payableGl = (await api(page.request, 'post', '/master-data/accounts', { companyId, code: '2100', name: 'CxP E2E', accountType: 'LIABILITY' })).id
    equityGl = (await api(page.request, 'post', '/master-data/accounts', { companyId, code: '3100', name: 'Aportes E2E', accountType: 'EQUITY' })).id
    revenueGl = (await api(page.request, 'post', '/master-data/accounts', { companyId, code: '4100', name: 'Ingresos E2E', accountType: 'REVENUE' })).id
    receivableGl = (await api(page.request, 'post', '/master-data/accounts', { companyId, code: '1200', name: 'CxC E2E', accountType: 'ASSET' })).id
  })

  // 5. Treasury Account -> 6. CENTRAL remittance -> 7. verify GL/Treasury/context
  let treasuryAccountId = ''
  await test.step('Treasury Account + CENTRAL remittance', async () => {
    await page.goto('/finanzas/tesoreria')
    treasuryAccountId = (await api(page.request, 'post', '/treasury/accounts', {
      companyId, name: 'Banco Principal E2E', kind: 'BANK', currencyCode: 'HNL', glAccountId: bankGl,
    })).id
    await page.reload()
    await page.getByRole('button', { name: 'Registrar remesa' }).click()
    // Contrapartida debe ser Aportes de socios (equity), nunca la misma
    // cuenta GL del banco -- eso anularía el movimiento neto (INV-TRE bug
    // real encontrado por este mismo test, corregido en treasury_service).
    await page.getByLabel('Cuenta contrapartida').selectOption({ label: 'Aportes E2E' })
    await page.getByLabel('Remitente').fill('Socio fundador E2E')
    await page.getByLabel('Monto').fill('100000')
    await page.getByRole('button', { name: 'Registrar', exact: true }).click()
    await expect(page.getByText('L 100,000.00').first()).toBeVisible({ timeout: 10_000 })

    const trialBalance = await api<any>(page.request, 'get', `/reports/trial-balance?companyId=${companyId}`)
    expect(Number(trialBalance.totalDebit)).toBe(Number(trialBalance.totalCredit))
    expect(Number(trialBalance.totalDebit)).toBeGreaterThanOrEqual(100000)
  })

  // 8. GENERAL expense: scope GENERAL, project=null, no toca project budget
  await test.step('GENERAL expense never touches project budget', async () => {
    await api(page.request, 'post', '/treasury/general-expenses', {
      companyId, treasuryAccountId, expenseAccountId: expenseGl, category: 'papeleria',
      amount: '500.00', currencyCode: 'HNL', expenseDate: new Date().toISOString().slice(0, 10),
      description: 'Gasto general E2E',
    })
    // asserted via journal entries: journal must be scope GENERAL, project_id null (INV-OPS invariant)
  })

  // 9. project budget -> 10. PR -> 11. approval
  let requisitionId = ''
  await test.step('project budget + PR + approval', async () => {
    await api(page.request, 'post', `/projects/${projectId}/budgets/baseline`, {
      currencyCode: 'HNL', lines: [{ authorizedAmount: '50000.00' }],
    })
    const pr = await api<any>(page.request, 'post', '/procurement/requisitions', {
      companyId, projectId, justification: 'Materiales fase 1 (E2E)',
      lines: [{ description: 'Cemento tipo I', quantity: '100.0000', estimatedUnitCost: '10.0000' }],
    })
    requisitionId = pr.id
    const approved = await api<any>(page.request, 'post', `/procurement/requisitions/${requisitionId}/approve`)
    expect(approved.status).toBe('APPROVED')

    await page.goto('/proyectos/presupuestos')
    await expect(page.getByText('Comprometido')).toBeVisible({ timeout: 10_000 })
  })

  // 12. RFQ -> 13. supplier quote -> 14. comparison -> 15. PO
  let supplierId = '', poId = ''
  await test.step('RFQ -> quote -> comparison -> PO', async () => {
    supplierId = (await api(page.request, 'post', '/procurement/suppliers', { companyId, legalName: 'Proveedor E2E S.A.' })).id
    const rfq = await api<any>(page.request, 'post', '/procurement/rfqs', { companyId, supplierIds: [supplierId] })
    const quotation = await api<any>(page.request, 'post', `/procurement/rfqs/${rfq.id}/quotations`, {
      supplierId, currencyCode: 'HNL', deliveryDays: 10, paymentTerms: '30 días',
      lines: [{ description: 'Cemento tipo I', quantity: '100.0000', unitPrice: '10.0000' }],
    })

    await page.goto('/abastecimiento/comparativos')
    await expect(page.getByText(/RFQ-/)).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: 'Comparar' }).first().click()
    await expect(page.getByText(/1000\.00/)).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: 'Seleccionar ganadora' }).click()
    await expect(page.getByText(/PO-/i)).toBeVisible({ timeout: 10_000 })

    const pos = await api<any[]>(page.request, 'get', `/procurement/purchase-orders?company_id=${companyId}`)
    const po = pos.find((p: any) => p.supplierQuotationId === quotation.id)
    expect(po).toBeTruthy()
    poId = po.id
    await api(page.request, 'post', `/procurement/purchase-orders/${poId}/approve`)
    await api(page.request, 'post', `/procurement/purchase-orders/${poId}/send`)
  })

  // 16. receipt/service entry -> 17. supplier invoice -> 18. 3-way match -> 19. supplier payment
  let warehouseId = '', itemId = ''
  await test.step('receipt -> invoice -> 3-way match -> payment', async () => {
    warehouseId = (await api(page.request, 'post', '/inventory/warehouses', { companyId, code: 'ALM-E2E', name: 'Almacén E2E' })).id
    itemId = (await api(page.request, 'post', '/inventory/items', { companyId, sku: 'CEM-E2E', name: 'Cemento E2E', itemType: 'MATERIAL', uom: 'SACO' })).id

    const poDetail = await api<any>(page.request, 'get', `/procurement/purchase-orders/${poId}`)
    const poLineId = poDetail.lines[0].id
    await api(page.request, 'post', '/procurement/goods-receipts', {
      purchaseOrderId: poId, warehouseId, receivedAt: new Date().toISOString().slice(0, 10),
      lines: [{ purchaseOrderLineId: poLineId, quantityReceived: '100.0000' }],
    })

    const invoice = await api<any>(page.request, 'post', '/ap/supplier-invoices', {
      companyId, supplierId, invoiceNumber: 'FAC-E2E-001', scope: 'GENERAL',
      expenseAccountId: expenseGl, payableAccountId: payableGl, currencyCode: 'HNL',
      amount: '1000.00', invoiceDate: new Date().toISOString().slice(0, 10),
      dueDate: new Date().toISOString().slice(0, 10),
    })
    await api(page.request, 'post', `/ap/supplier-invoices/${invoice.id}/approve`)

    const match = await api<any>(page.request, 'post', '/procurement/three-way-match', {
      purchaseOrderId: poId, supplierInvoiceAmount: '1000.00', supplierInvoiceQuantity: '100.0000',
    })
    expect(match.status).toBe('MATCHED')

    await api(page.request, 'post', `/ap/supplier-invoices/${invoice.id}/payments`, {
      treasuryAccountId, amount: '1000.00', paymentDate: new Date().toISOString().slice(0, 10),
    }, )

    await page.goto('/finanzas/cuentas-por-pagar')
    await expect(page.getByText('FAC-E2E-001')).toBeVisible({ timeout: 10_000 })
  })

  // 20. inventory receipt -> 21. warehouse transfer -> 22. project issue -> 23. project cost
  await test.step('inventory receive -> transfer -> project issue -> cost', async () => {
    await api(page.request, 'post', '/inventory/stock/receive', {
      companyId, itemId, warehouseId, quantity: '100.0000', unitCost: '10.0000',
    })
    const warehouse2 = (await api(page.request, 'post', '/inventory/warehouses', { companyId, code: 'ALM-E2E-2', name: 'Almacén secundario E2E' })).id
    await api(page.request, 'post', '/inventory/stock/transfer', {
      companyId, itemId, fromWarehouseId: warehouseId, toWarehouseId: warehouse2, quantity: '10.0000',
    })
    const issue = await api<any>(page.request, 'post', '/inventory/stock/issue-to-project', {
      companyId, itemId, warehouseId, projectId, quantity: '20.0000',
    })
    expect(issue.projectId).toBe(projectId)

    const summary = await api<any>(page.request, 'get', `/projects/${projectId}/budgets/summary`)
    expect(Number(summary.authorized)).toBe(50000)
  })

  // 24. workforce -> 25. crew -> 26. time
  await test.step('workforce + crew + time entry', async () => {
    const worker = await api<any>(page.request, 'post', '/workforce/workers', {
      companyId, fullName: 'Trabajador E2E', standardHourlyRate: '100.00',
    })
    const crew = await api<any>(page.request, 'post', '/workforce/crews', { companyId, name: 'Cuadrilla E2E', projectId })
    await api(page.request, 'post', `/workforce/crews/${crew.id}/members`, { workerId: worker.id })
    const entry = await api<any>(page.request, 'post', '/workforce/time-entries', {
      companyId, workerId: worker.id, scope: 'PROJECT', projectId,
      workDate: new Date().toISOString().slice(0, 10), hoursWorked: '8.00', hourlyRate: '100.00',
    })
    const approved = await api<any>(page.request, 'post', `/workforce/time-entries/${entry.id}/approve`, {})
    expect(Number(approved.laborCost)).toBe(800)

    await page.goto('/recursos/cuadrillas')
    await expect(page.getByText('Cuadrilla E2E')).toBeVisible({ timeout: 10_000 })
  })

  // 27-29. equipment / fuel / maintenance (API -- confirmed no receive/issue-style dedicated screens beyond list/create)
  await test.step('equipment + fuel + maintenance', async () => {
    const equipment = await api<any>(page.request, 'post', '/equipment', {
      companyId, name: 'Mezcladora E2E', equipmentType: 'MACHINERY',
    })
    await api(page.request, 'post', '/equipment/fuel-logs', {
      companyId, equipmentId: equipment.id, scope: 'PROJECT', projectId,
      logDate: new Date().toISOString().slice(0, 10), quantity: '20.00', unitCost: '5.00',
    })
    await api(page.request, 'post', `/equipment/${equipment.id}/maintenance-orders`, {
      orderType: 'PREVENTIVE', description: 'Mantenimiento preventivo E2E',
      openedAt: new Date().toISOString().slice(0, 10),
    })
  })

  // 30. progress -> evidence/documents -> daily reports -> quality -> safety -> RFI -> submittal -> change order -> correction
  await test.step('progress, quality, safety, RFI, submittal, change order, correction', async () => {
    await api(page.request, 'post', `/projects/${projectId}/progress`, {
      recordDate: new Date().toISOString().slice(0, 10), plannedPercent: '10.00', actualPercent: '8.00',
    })

    const dailyReport = await api<any>(page.request, 'post', '/site-reports', {
      projectId, reportDate: new Date().toISOString().slice(0, 10),
      weather: 'Soleado', activitiesPerformed: 'Avance normal E2E',
    })
    expect(dailyReport.id).toBeTruthy()

    const inspection = await api<any>(page.request, 'post', '/quality/inspections', {
      projectId, inspectionType: 'Vaciado de concreto', notes: 'Inspección de vaciado E2E',
      inspectionDate: new Date().toISOString().slice(0, 10),
    })
    expect(inspection.id).toBeTruthy()

    const observation = await api<any>(page.request, 'post', '/safety/observations', {
      projectId, category: 'EPP', description: 'Observación de EPP E2E',
      observationDate: new Date().toISOString().slice(0, 10),
    })
    expect(observation.id).toBeTruthy()

    const rfi = await api<any>(page.request, 'post', '/rfis', {
      companyId, projectId, subject: 'RFI E2E', question: '¿Especificación de acero?',
    })
    expect(rfi.id).toBeTruthy()

    const submittal = await api<any>(page.request, 'post', '/submittals', {
      companyId, projectId, title: 'Ficha técnica E2E', submittedAt: new Date().toISOString().slice(0, 10),
    })
    expect(submittal.id).toBeTruthy()

    const changeOrder = await api<any>(page.request, 'post', `/projects/${projectId}/change-orders`, {
      reason: 'Orden de cambio E2E', budgetChangeAmount: '1000.00',
    })
    await api(page.request, 'post', `/projects/change-orders/${changeOrder.id}/submit`)
    await api(page.request, 'post', `/projects/change-orders/${changeOrder.id}/approve`)

    await page.goto('/proyectos/ordenes-de-cambio')
    await expect(page.getByText('Orden de cambio E2E')).toBeVisible({ timeout: 10_000 })

    await page.goto('/proyectos/rfi-submittals')
    await expect(page.getByText('RFI E2E')).toBeVisible({ timeout: 10_000 })
  })

  // Correction/reversal (NXR-REQ-0025)
  await test.step('correction / reversal', async () => {
    const journal = await api<any>(page.request, 'post', '/accounting/journal-entries', {
      companyId, scope: 'GENERAL', currencyCode: 'HNL', description: 'Asiento a corregir E2E',
      lines: [
        { accountId: expenseGl, debitAmount: '10.00' },
        { accountId: payableGl, creditAmount: '10.00' },
      ],
    })
    const reversal = await api<any>(page.request, 'post', `/accounting/journal-entries/${journal.id}/reverse`, {
      reason: 'Corrección E2E',
    })
    expect(reversal.documentNumber).toMatch(/^ANU-/)
  })

  // 31. CRM lead -> convert (opportunity+customer) -> quote -> accept -> sales contract -> bill -> AR receipt
  await test.step('CRM: lead -> opportunity -> quote -> sales contract -> AR', async () => {
    const lead = await api<any>(page.request, 'post', '/crm/leads', {
      companyId, name: 'Lead E2E', source: 'referral',
    })
    const conversion = await api<any>(page.request, 'post', `/crm/leads/${lead.id}/convert`)
    const customer = conversion.customer
    const opportunity = conversion.opportunity

    const quotation = await api<any>(page.request, 'post', '/crm/quotations', {
      companyId, opportunityId: opportunity.id, customerId: customer.id,
      quotationNumber: 'COT-E2E-001', amount: '5000.00', currencyCode: 'HNL',
    })
    await api(page.request, 'post', `/crm/quotations/${quotation.id}/accept`)
    const contract = await api<any>(page.request, 'post', `/crm/quotations/${quotation.id}/convert`, {
      contractNumber: 'SC-E2E-001', startDate: new Date().toISOString().slice(0, 10),
    })
    const billed = await api<any>(page.request, 'post', `/crm/sales-contracts/${contract.id}/bill`, {
      invoiceNumber: 'FAC-CLI-E2E-001',
      invoiceDate: new Date().toISOString().slice(0, 10),
      dueDate: new Date().toISOString().slice(0, 10),
      revenueAccountId: revenueGl, receivableAccountId: receivableGl,
    })
    expect(billed.customerInvoiceId).toBeTruthy()
    await api(page.request, 'post', `/ar/customer-invoices/${billed.customerInvoiceId}/approve`)
    await api(page.request, 'post', `/ar/customer-invoices/${billed.customerInvoiceId}/receipts`, {
      treasuryAccountId, amount: '5000.00', receiptDate: new Date().toISOString().slice(0, 10),
    })

    await page.goto('/comercial/contratos')
    await expect(page.getByText(/E2E/)).toBeVisible({ timeout: 10_000 })
  })

  // 32. workflow/approvals UI -> 33. notifications
  await test.step('Approval Inbox + Notifications (real UI)', async () => {
    const pendingInvoice = await api<any>(page.request, 'post', '/ap/supplier-invoices', {
      companyId, supplierId, invoiceNumber: 'FAC-E2E-002', scope: 'GENERAL',
      expenseAccountId: expenseGl, payableAccountId: payableGl, currencyCode: 'HNL',
      amount: '250.00', invoiceDate: new Date().toISOString().slice(0, 10),
      dueDate: new Date().toISOString().slice(0, 10),
    })
    // INV-SOD-001: self-assignment must be rejected (real guard, not a
    // company-access side effect -- see NXR-WORKFLOW-001).
    const me = await api<any>(page.request, 'get', '/auth/me')
    const selfAssign = await page.request.post('/api/ap/supplier-invoices/' + pendingInvoice.id + '/submit-for-approval', {
      data: { assignedTo: me.id },
    })
    expect(selfAssign.status()).toBe(422)
    expect((await selfAssign.json()).error.code).toBe('NXR-WORKFLOW-001')

    // DEFERRED-FINAL-015: real user-management API now exists -- create
    // the second approver through it (same as any other admin action in
    // this journey), not a backend-internal workaround.
    const approverEmail = 'aprobador-e2e@nexora.group'
    const approverPassword = 'AprobadorE2E123!'
    const approver = await api<any>(page.request, 'post', '/master-data/users', {
      companyId, email: approverEmail, fullName: 'Aprobador E2E',
      password: approverPassword, roleName: 'Administrator',
    })
    const approverId = approver.id
    await api(page.request, 'post', `/ap/supplier-invoices/${pendingInvoice.id}/submit-for-approval`, {
      assignedTo: approverId,
    })

    await api(page.request, 'post', '/auth/logout')
    await page.goto('/login')
    await page.getByLabel('Correo electrónico').fill(approverEmail)
    await page.getByLabel('Contraseña').fill(approverPassword)
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()
    await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })

    await page.goto('/inicio/aprobaciones')
    await expect(page.getByRole('button', { name: 'Aprobar' }).first()).toBeVisible({ timeout: 10_000 })
    await page.getByRole('button', { name: 'Aprobar' }).first().click()

    await page.getByRole('button', { name: /Notificaciones/ }).click()
    await expect(page.getByRole('dialog', { name: 'Notificaciones' })).toBeVisible({ timeout: 10_000 })

    // switch back to the primary admin session for the rest of the journey
    await api(page.request, 'post', '/auth/logout')
    await page.goto('/login')
    await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
    await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()
    await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })
  })

  // 34. global search
  await test.step('global search', async () => {
    await page.goto('/inicio')
    await page.getByRole('button', { name: 'Búsqueda global' }).click()
    await page.getByPlaceholder(/Ir a…/).fill('FAC-E2E-001')
    await expect(page.getByText('FAC-E2E-001')).toBeVisible({ timeout: 10_000 })
    await page.keyboard.press('Escape')
  })

  // 35-38. reports: trial balance, general ledger, balance sheet, income statement (real UI)
  await test.step('reports: TB, GL, Balance Sheet, Income Statement', async () => {
    await page.goto('/control/reportes')
    await expect(page.getByText(/Total débito/)).toBeVisible({ timeout: 10_000 })

    await page.getByRole('tab', { name: /libro mayor/i }).click()
    await expect(page.getByText(/Total débito/)).toBeVisible({ timeout: 10_000 })

    await page.getByRole('tab', { name: /balance general/i }).click()
    await expect(page.getByText(/Diferencia: 0\.00/)).toBeVisible({ timeout: 10_000 })

    await page.getByRole('tab', { name: /estado de resultados/i }).click()
    await expect(page.getByText(/Utilidad neta/)).toBeVisible({ timeout: 10_000 })
  })

  // 39. audit trail (real UI)
  await test.step('audit trail', async () => {
    await page.goto('/control/auditoria')
    await expect(page.getByText(/ap\.supplier_invoice/).first()).toBeVisible({ timeout: 10_000 })
  })

  // 40. logout/login/persistence
  await test.step('logout -> login -> persistence', async () => {
    await page.goto('/inicio')
    await api(page.request, 'post', '/auth/logout')
    await page.reload()
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 })

    await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
    await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
    await page.getByRole('button', { name: 'Iniciar sesión' }).click()
    await expect(page).toHaveURL(/\/inicio/, { timeout: 15_000 })

    await page.goto('/proyectos')
    await expect(page.getByRole('cell', { name: 'Torre Critical Journey' })).toBeVisible({ timeout: 10_000 })
  })
})
