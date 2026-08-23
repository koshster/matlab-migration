import '@testing-library/jest-dom'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { server } from '../mocks/server'

// The admin handlers hold mutable in-memory state, so tests that mutate the
// roster must not leak into each other. Vitest isolates modules per test file
// by default, which keeps that state per-file.
beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
})
afterEach(() => {
  server.resetHandlers()
})
afterAll(() => {
  server.close()
})
