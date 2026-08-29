import { pbkdf2Sync, randomBytes } from 'crypto'
import path from 'path'
import { fileURLToPath } from 'url'
import { defineConfig, devices } from '@playwright/test'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/**
 * NXR-REQ-0112/0113 (E2E + Critical Journey). Corre contra un backend +
 * frontend reales levantados exclusivamente para este suite (puertos y
 * base de datos propios, nunca la DB de desarrollo ni la de pytest) --
 * ver e2e/README.md para el setup exacto. Un solo worker: el Critical
 * Journey es un recorrido secuencial con estado real (mismo login, mismo
 * proyecto), no tests aislados que puedan correr en paralelo.
 */
const E2E_BACKEND_PORT = 8010
const E2E_FRONTEND_PORT = 5175
const E2E_FRONTEND_URL = `http://localhost:${E2E_FRONTEND_PORT}`
const E2E_BACKEND_URL = `http://localhost:${E2E_BACKEND_PORT}`

// Protected Edit never uses a repository/test fixture secret. A fresh token,
// salt and PBKDF2 digest are generated for each Playwright process. The token
// remains process-local; the backend receives only its salt/digest through the
// child-process environment, exactly like production receives Key Vault refs.
const E2E_EDIT_ACCESS_TOKEN = randomBytes(18).toString('base64url').slice(0, 24)
const E2E_EDIT_ACCESS_SALT_BYTES = randomBytes(16)
const E2E_EDIT_ACCESS_SALT = E2E_EDIT_ACCESS_SALT_BYTES.toString('base64url')
const E2E_EDIT_ACCESS_DIGEST = pbkdf2Sync(
  E2E_EDIT_ACCESS_TOKEN,
  E2E_EDIT_ACCESS_SALT_BYTES,
  250_000,
  32,
  'sha256',
).toString('base64url')
process.env.E2E_EDIT_ACCESS_TOKEN = E2E_EDIT_ACCESS_TOKEN

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'e2e-report' }]],
  timeout: 60_000,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? E2E_FRONTEND_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      // Fresh DB real (drop+create) en cada corrida, luego el mismo
      // comando que backend/Dockerfile's CMD: alembic upgrade head sobre
      // una DB vacía (fresh-install path real) antes de servir.
      command: `dropdb --if-exists nexora_e2e && createdb nexora_e2e && cd ../backend && DATABASE_URL=postgresql+psycopg://nexora@localhost:5432/nexora_e2e FRONTEND_URL=${E2E_FRONTEND_URL} BOOTSTRAP_ADMIN_EMAIL=admin@nexora.group BOOTSTRAP_ADMIN_PASSWORD=NexoraAdmin123! APP_ENV=development ./.venv/bin/alembic upgrade head && DATABASE_URL=postgresql+psycopg://nexora@localhost:5432/nexora_e2e FRONTEND_URL=${E2E_FRONTEND_URL} BOOTSTRAP_ADMIN_EMAIL=admin@nexora.group BOOTSTRAP_ADMIN_PASSWORD=NexoraAdmin123! APP_ENV=development ./.venv/bin/uvicorn app.main:app --port ${E2E_BACKEND_PORT}`,
      env: {
        ...process.env,
        EDIT_ACCESS_TOKEN_SALT: E2E_EDIT_ACCESS_SALT,
        EDIT_ACCESS_TOKEN_DIGEST: E2E_EDIT_ACCESS_DIGEST,
      },
      url: `${E2E_BACKEND_URL}/readyz`,
      reuseExistingServer: false,
      timeout: 60_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
    {
      command: `VITE_API_PROXY_TARGET=${E2E_BACKEND_URL} npx vite --port ${E2E_FRONTEND_PORT} --strictPort`,
      url: E2E_FRONTEND_URL,
      reuseExistingServer: false,
      timeout: 60_000,
      stdout: 'pipe',
      stderr: 'pipe',
    },
  ],
})
