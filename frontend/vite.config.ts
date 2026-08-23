import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// Vitest config lives in vitest.config.ts. Keeping `test` out of this file lets
// vite.config.ts stay typed against vite 6, while vitest 2 (which bundles vite 5
// types) types its own config separately.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@statics/contract': resolve(__dirname, '../packages/contract'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
})
