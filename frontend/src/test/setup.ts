import '@testing-library/jest-dom'
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest'
import { server } from '../mocks/server'
import { resetAdminMockState } from '../mocks/adminHandlers'
import { resetAssignmentMockState } from '../mocks/assignmentHandlers'
import { resetStudentMockState } from '../mocks/studentHandlers'

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' })
})

// The handlers hold mutable in-memory state so the UI behaves like a real
// backend within a session. Vitest isolates modules per file but not per test,
// so reset between tests — otherwise a test that accepts an invitation or drops
// a student silently changes what later tests see.
beforeEach(() => {
  resetAdminMockState()
  resetStudentMockState()
  resetAssignmentMockState()
})

afterEach(() => {
  server.resetHandlers()
})

afterAll(() => {
  server.close()
})
