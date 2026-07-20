import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: 'index.html',
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    css: false,
    // Pin env vars the components read at module load so tests never depend on
    // a local .env. CI has no .env, which would otherwise change behaviour
    // (e.g. LoginPage falls back to its "not configured" branch).
    env: {
      VITE_API_URL: 'http://testserver',
      VITE_GOOGLE_CLIENT_ID: 'test-client-id',
    },
    // Playwright specs live in e2e/ and run via `npm run test:e2e`, not vitest.
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
  },
})
