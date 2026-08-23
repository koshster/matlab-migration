import { setupServer } from 'msw/node'
import { handlers } from './handlers'

/** Node-side counterpart to `browser.ts`, for component tests. */
export const server = setupServer(...handlers)
