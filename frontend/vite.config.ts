import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'pwa-icon.svg'],
      manifest: {
        name: 'Nexora Group — Gestión Empresarial y Control de Construcción',
        short_name: 'Nexora',
        description: 'Plataforma administrativa Nexora Group: tesorería, proyectos, abastecimiento y control de obra.',
        theme_color: '#0B1F3A',
        background_color: '#0B1F3A',
        display: 'standalone',
        start_url: '/',
        icons: [
          {
            src: '/pwa-icon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'any',
          },
          {
            src: '/pwa-icon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        // Nexora is an online transactional ERP. Never precache the SPA HTML
        // or JavaScript/CSS application shell: doing so can keep an old bundle
        // alive after a deployment and make it call the obsolete same-origin
        // /api proxy. Static Web Apps owns navigation fallback and HTTP cache
        // headers; the service worker only keeps install metadata/icons.
        globPatterns: ['**/*.{svg,png,webmanifest}'],
        navigateFallback: null,
        cleanupOutdatedCaches: true,
        clientsClaim: true,
        skipWaiting: true,
        runtimeCaching: [
          {
            urlPattern: /\/api\//,
            handler: 'NetworkOnly',
          },
        ],
      },
    }),
  ],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./tests/setup.ts'],
    css: true,
    exclude: ['**/node_modules/**', 'e2e/**'],
  },
})
