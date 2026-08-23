import { defineConfig } from 'vitest/config'
import { resolve } from 'path'

// Separate from vite.config.ts: vitest 2 ships vite 5 types, which conflict with
// the vite 6 the app builds against. Keeping the two configs apart avoids a
// vitest major bump (and the ADR that would require) just to satisfy typecheck.
// The contract alias is repeated here because this config replaces, not extends,
// vite.config.ts when vitest runs.
export default defineConfig({
  resolve: {
    alias: {
      '@statics/contract': resolve(__dirname, '../packages/contract'),
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
