import '@testing-library/jest-dom/vitest'

// Happy DOM 20 no longer installs the browser confirmation API by default.
// Keep the shared test environment faithful to a real browser so interaction
// tests can spy on (and explicitly decide) destructive confirmations.
Object.defineProperty(window, 'confirm', {
  configurable: true,
  writable: true,
  value: () => false,
})
