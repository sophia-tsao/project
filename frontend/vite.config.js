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
    // Playwright specs live in e2e/ and run via `npm run test:e2e`, not vitest.
    exclude: ['e2e/**', 'node_modules/**', 'dist/**'],
  },
})
