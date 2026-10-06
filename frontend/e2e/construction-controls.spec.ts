import { expect, test, type APIRequestContext } from '@playwright/test'

const ADMIN_EMAIL = 'admin@nexora.group'
const ADMIN_PASSWORD = 'NexoraAdmin123!'

async function unlock(request: APIRequestContext): Promise<string> {
  const token = process.env.E2E_EDIT_ACCESS_TOKEN
  expect(token).toBeTruthy()
  const response = await request.post('/api/edit-access/verify', { data: { token } })
  expect(response.ok(), await response.text()).toBeTruthy()
  const body = await response.json()
  expect(body.capability).toBeTruthy()
  return body.capability
}

async function mutation(
  request: APIRequestContext,
  capability: string,
  method: 'post' | 'patch' | 'put',
  path: string,
  data: unknown,
) {
  const response = await request[method](`/api${path}`, {
    data,
    headers: { 'X-Nexora-Edit-Access': capability },
  })
  expect(response.ok(), `${method.toUpperCase()} ${path}: ${response.status()} ${await response.text()}`).toBeTruthy()
  return response.json()
}

test('Construction controls: RFI and Submittal real lifecycle + audit-safe transitions', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Correo electrónico').fill(ADMIN_EMAIL)
  await page.getByLabel('Contraseña').fill(ADMIN_PASSWORD)
  await page.getByRole('button', { name: 'Iniciar sesión' }).click()
  await expect(page).toHaveURL(/\/inicio/)

  const capability = await unlock(page.request)
  const company = await mutation(page.request, capability, 'post', '/master-data/companies', {
    name: 'Construction Controls E2E',
    functionalCurrencyCode: 'HNL',
  })

  const project = await mutation(page.request, capability, 'post', '/projects', {
    companyId: company.id,
    name: 'Construction Controls Project',
    code: 'CC-E2E-001',
    currencyCode: 'HNL',
  })

  const rfi = await mutation(page.request, capability, 'post', '/rfis', {
    companyId: company.id,
    projectId: project.id,
    subject: 'RFI E2E — detalle de ejecución',
    question: 'Confirmar detalle constructivo para la prueba E2E.',
    responsible: 'Construction Controls E2E',
    dueDate: '2026-10-10',
  })
  expect(rfi.status).toBe('OPEN')

  const respondedRfi = await mutation(page.request, capability, 'post', `/rfis/${rfi.id}/respond`, {
    response: 'Respuesta técnica registrada por el responsable E2E.',
  })
  expect(respondedRfi.status).toBe('ANSWERED')

  const closedRfi = await mutation(page.request, capability, 'post', `/rfis/${rfi.id}/close`, {})
  expect(closedRfi.status).toBe('CLOSED')

  const submittal = await mutation(page.request, capability, 'post', '/submittals', {
    companyId: company.id,
    projectId: project.id,
    title: 'Submittal E2E — material de prueba',
    description: 'Submittal creado por el recorrido de certificación.',
    submittedAt: '2026-10-06',
    dueDate: '2026-10-12',
  })
  expect(submittal.status).toBe('SUBMITTED')

  const respondedSubmittal = await mutation(page.request, capability, 'post', `/submittals/${submittal.id}/response`, {
    response: 'Revisión técnica registrada por el revisor E2E.',
  })
  expect(respondedSubmittal.status).toBe('UNDER_REVIEW')

  const decidedSubmittal = await mutation(page.request, capability, 'post', `/submittals/${submittal.id}/decision`, {
    decision: 'APPROVED',
  })
  expect(decidedSubmittal.status).toBe('APPROVED')

  const rfis = await page.request.get(`/api/rfis?companyId=${company.id}&projectId=${project.id}`)
  expect(rfis.ok()).toBeTruthy()
  expect((await rfis.json()).some((item: { id: string; status: string }) => item.id === rfi.id && item.status === 'CLOSED')).toBeTruthy()

  const submittals = await page.request.get(`/api/submittals?companyId=${company.id}&projectId=${project.id}`)
  expect(submittals.ok()).toBeTruthy()
  expect((await submittals.json()).some((item: { id: string; status: string }) => item.id === submittal.id && item.status === 'APPROVED')).toBeTruthy()
})
