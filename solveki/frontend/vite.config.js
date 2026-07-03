import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../myapp/static/myapp',
    emptyOutDir: false,
    manifest: true,
    rollupOptions: {
      input: 'src/main.jsx',
    },
  },
})
