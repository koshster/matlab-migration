import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider, QueryCache } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App'
import { ApiError } from './api/client'

async function enableMocking() {
  if (import.meta.env.DEV && import.meta.env.VITE_MSW !== 'false') {
    const { worker } = await import('./mocks/browser')
    return worker.start({ onUnhandledRequest: 'warn' })
  }
}

// Students and instructors have separate sessions and separate login screens,
// so an expired session must clear the right one and land on the right page.
// This previously always cleared `statics_session` and redirected to
// /student/login, which bounced an instructor out of the admin area entirely.
function handleUnauthorized() {
  const onAdminRoute = window.location.pathname.startsWith('/admin')
  if (onAdminRoute) {
    sessionStorage.removeItem('instructor_session')
    window.location.replace('/admin/login')
    return
  }
  localStorage.removeItem('statics_session')
  window.location.replace('/student/login')
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401) {
        handleUnauthorized()
      }
    },
  }),
  defaultOptions: {
    queries: {
      retry: (failureCount, error) =>
        error instanceof ApiError && error.status === 401 ? false : failureCount < 2,
      staleTime: 30_000,
    },
  },
})

const rootEl = document.getElementById('root')
if (!rootEl) throw new Error('Root element not found')

void enableMocking().then(() => {
  createRoot(rootEl).render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </StrictMode>,
  )
})
